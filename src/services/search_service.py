from typing import Tuple

from src.core.config import settings
from src.schemas.models import (
    SearchDayResultsParams,
    SearchDayResultsResponse,
    SearchCalendarPricesResponse,
    SearchCalendarPricesParams,
    CalendarDay,
    SearchSummaryParams,
    SearchCheapestSummaryResponse,
    CheapestSummary,
    SearchFastestSummaryResponse,
    FastestSummary,
    BaseSearchParams,
    ResolvePositionsParams, CheapestPriceInfo, FastestVsCheapestInfo,
)
from src.schemas.enums import JourneyType
from src.core.exceptions import InvalidInputError, LocationResolutionError, UpstreamApiError
from src.http.discovery_client import DiscoveryApiClient
from src.services.position_service import LocationService
from src.utils.validator import validate_date_range
from src.utils.normalizer import prepare_common_api_params, shape_day_results, normalize_calendar_day_results, \
    normalize_cheapest_summary_results, normalize_fastest_summary_results
from src.core.logger import logger


class SearchService:

    def __init__(self, client: DiscoveryApiClient, location_service: LocationService):
        self._client = client
        self._location_service = location_service

    async def search_day_results(self, params: SearchDayResultsParams) -> SearchDayResultsResponse:
        logger.info(f"[Search] Starting 'search_day_results' with params: {params.model_dump()}")
        from_id, to_id = await self._ensure_position_ids(params)
        logger.debug(f"[Search] Resolved positions: from_id={from_id}, to_id={to_id}")

        api_params = prepare_common_api_params(params, from_id, to_id)
        api_params.update({
            "outboundDate": params.date_out
        })
        if params.date_return:
            api_params["inboundDate"] = params.date_return

        endpoint = settings.SEARCH_DAY_RESULTS_ENDPOINT

        try:
            logger.debug(f"[Search] Sending GET request to {endpoint} with params: {api_params}")
            raw_data = await self._client.get(endpoint, params=api_params)
            #logger.debug(f"[Search] search_day_results response: {raw_data}")
        except UpstreamApiError as e:
            logger.error(f"[Search] Upstream API error during {endpoint} request: {e}")
            raise

        results = shape_day_results(raw_data)
        logger.info(f"[Search] Retrieved {len(results)}")
        logger.info(f"[Search] Retrieved {results[0]}")

        return SearchDayResultsResponse(
            resolved_from_id=from_id,
            resolved_to_id=to_id,
            results=results,
            note="Prices are estimates and subject to change. Times are local to departure/arrival cities."
        )

    async def search_calendar_prices(self, params: SearchCalendarPricesParams) -> SearchCalendarPricesResponse:
        logger.info(f"[Search] Starting 'search_calendar_prices' with params: {params.model_dump()}")
        validate_date_range(params.date_start, params.date_end, max_days=31)

        journey_type = params.journey_type or JourneyType.ONE_WAY
        from_id, to_id = await self._ensure_position_ids(params)
        logger.debug(f"[Search] Resolved positions: from_id={from_id}, to_id={to_id}")

        api_params = prepare_common_api_params(params, from_id, to_id)
        api_params.update({
            "calendarDateStart": params.date_start,
            "calendarDateEnd": params.date_end,
            "journeyType": journey_type.value
        })

        endpoint = settings.SEARCH_CALENDAR_PRICES_ENDPOINT

        try:
            logger.debug(f"[Search] Sending GET request to {endpoint} with params: {api_params}")
            raw_data = await self._client.get(endpoint, params=api_params)
            logger.debug(f"[Search] search_calendar_prices response: {raw_data}")
        except UpstreamApiError as e:
            logger.error(f"[Search] Upstream API error during {endpoint} request: {e}")
            raise

        normalized, count = normalize_calendar_day_results(raw_data)
        logger.info(f"[Search] Normalized {count} calendar days")

        calendar_days = []
        for item in normalized["calendar"]:
            try:
                calendar_day = CalendarDay(
                    date=item["date"],
                    priceCents=item["priceCents"],
                    currency=item["currency"],
                )
                calendar_days.append(calendar_day)
            except Exception as e:
                logger.error(f"[Search] Failed to create CalendarDay: {e}, data: {item}")
                continue

        logger.debug(f"[Search] Created {len(calendar_days)} CalendarDay objects")

        stats = normalized.get("stats", {})
        min_price = stats.get("min_price")
        max_price = stats.get("max_price")

        if min_price and max_price:
            note = (
                f"Prices represent the lowest available fares within selected period. "
                f"Range: {min_price:.2f} - {max_price:.2f} {normalized['currency']}"
            )
        else:
            note = "Prices represent the lowest available fares within selected period."

        return SearchCalendarPricesResponse(
            resolved_from_id=from_id,
            resolved_to_id=to_id,
            calendar=calendar_days,
            note=note,
        )

    async def search_cheapest_summary(self, params: SearchSummaryParams) -> SearchCheapestSummaryResponse:
        logger.info(f"[Search] Starting 'search_cheapest_summary' with params: {params.model_dump()}")
        validate_date_range(params.date_start, params.date_end, max_days=30)
        from_id, to_id = await self._ensure_position_ids(params)
        logger.debug(f"[Search] Resolved positions: from_id={from_id}, to_id={to_id}")

        api_params = prepare_common_api_params(params, from_id, to_id)
        api_params.update({
            "outboundDateStart": params.date_start,
            "inboundDateEnd": params.date_end
        })

        endpoint = settings.DISCOVERY_CHEAPEST_SUMMARY_ENDPOINT

        try:
            logger.debug(f"[Search] Sending GET request to {endpoint} with params: {api_params}")
            raw_data = await self._client.get(endpoint, params=api_params)
            logger.debug(f"[Search] search_cheapest_summary response keys: {list(raw_data.keys())}")
        except UpstreamApiError as e:
            logger.error(f"[Search] Upstream API error during {endpoint}: {e}")
            raise

        normalized, stats = normalize_cheapest_summary_results(raw_data, params.currency)
        logger.info(
            f"[Search] Cheapest summary retrieved: {stats['total_dates']} dates, "
            f"{stats['total_modes']} transport options"
        )

        summary_dict = {}

        for date, modes_data in normalized["summary"].items():
            summary_dict[date] = {}

            for mode, price_info in modes_data.items():
                summary_dict[date][mode] = CheapestPriceInfo(
                    min_price=price_info["min_price"],
                    currency=price_info["currency"],
                )

        cheapest_summary = CheapestSummary(summary=summary_dict)

        insight = None
        if stats.get("cheapest_date") and stats.get("cheapest_mode"):
            min_price = stats["min_price_overall"]
            max_price = stats["max_price_overall"]

            insight = (
                f"Best deal: {stats['cheapest_date']} via {stats['cheapest_mode']} "
                f"at {min_price:.2f} {params.currency}. "
                f"Price range: {min_price:.2f} - {max_price:.2f} {params.currency}. "
                f"Total {stats['total_results']} options across {stats['total_dates']} dates."
            )

            mode_info = []
            for mode, mode_stats in stats["by_mode"].items():
                mode_info.append(
                    f"{mode}: {mode_stats['count']} dates, "
                    f"{mode_stats['min_price']:.2f}-{mode_stats['max_price']:.2f} {params.currency}"
                )

            if mode_info:
                insight += f" Breakdown: {'; '.join(mode_info)}."
        else:
            insight = "No pricing data available for the selected date range and routes."

        logger.debug(f"[Search] Generated insight: {insight}")

        return SearchCheapestSummaryResponse(
            resolved_from_id=from_id,
            resolved_to_id=to_id,
            summary=cheapest_summary,
            insight=insight,
        )

    async def search_fastest_summary(self, params: SearchSummaryParams) -> SearchFastestSummaryResponse:
        logger.info(f"[Search] Starting 'search_fastest_summary' with params: {params.model_dump()}")
        validate_date_range(params.date_start, params.date_end, max_days=30)
        from_id, to_id = await self._ensure_position_ids(params)
        logger.debug(f"[Search] Resolved positions: from_id={from_id}, to_id={to_id}")

        api_params = prepare_common_api_params(params, from_id, to_id)
        api_params.update({
            "outboundDateStart": params.date_start,
            "inboundDateEnd": params.date_end
        })

        endpoint = settings.DISCOVERY_FASTEST_SUMMARY_ENDPOINT

        try:
            logger.debug(f"[Search] Sending GET request to {endpoint} with params: {api_params}")
            raw_data = await self._client.get(endpoint, params=api_params)
            logger.debug(f"[Search] search_fastest_summary response keys: {list(raw_data.keys())}")
        except UpstreamApiError as e:
            logger.error(f"[Search] Upstream API error during /fastest-summary request: {e}")
            raise

        normalized = normalize_fastest_summary_results(raw_data, params.currency)
        logger.info(f"[Search] Normalized {len(normalized['summary'])} dates")

        summary_dict = {}

        for date, modes_data in normalized["summary"].items():
            summary_dict[date] = {}

            for mode, info in modes_data.items():
                summary_dict[date][mode] = FastestVsCheapestInfo(
                    fastest_duration=info["fastest_duration"],
                    fastest_price=info["fastest_price"],
                    cheapest_price=info["cheapest_price"],
                    currency=info["currency"],
                )

        fastest_summary = FastestSummary(summary=summary_dict)
        logger.info("[Search] Fastest summary retrieved successfully")

        return SearchFastestSummaryResponse(
            resolved_from_id=from_id,
            resolved_to_id=to_id,
            summary=fastest_summary,
            note="This summary helps compare the trade-offs between speed and cost for different modes of transport."
        )

    async def _ensure_position_ids(self, params) -> tuple[int, int]:
        if params.from_id and params.to_id:
            logger.debug(f"[Search] Using provided IDs: from_id={params.from_id}, to_id={params.to_id}")
            return params.from_id, params.to_id

        if params.from_term and params.to_term:
            logger.info(f"[Search] Resolving positions for '{params.from_term}' → '{params.to_term}'")

            try:
                resolve_params = ResolvePositionsParams(
                    from_term=params.from_term,
                    to_term=params.to_term,
                    locale=params.locale
                )
                resolved = await self._location_service.resolve_positions(resolve_params)

                if not resolved.suggestion.from_id or not resolved.suggestion.to_id:
                    raise LocationResolutionError(
                        f"Could not resolve locations for '{params.from_term}' → '{params.to_term}'"
                    )

                from_id = resolved.suggestion.from_id
                to_id = resolved.suggestion.to_id

                logger.info(
                    f"[Search] Resolved: '{params.from_term}' → {from_id}, "
                    f"'{params.to_term}' → {to_id}"
                )

                return from_id, to_id

            except Exception as e:
                logger.error(f"[Search] Failed to resolve positions: {e}")
                raise LocationResolutionError(
                    f"Could not resolve locations for '{params.from_term}' → '{params.to_term}'"
                ) from e

        raise LocationResolutionError(
            "Must provide either (from_id, to_id) or (from_term, to_term)"
        )