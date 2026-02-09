from src.core.config import settings
from src.core.logger import logger
from src.schemas.models import (
    AutocompleteParams,
    AutocompleteResponse,
    ResolvePositionsParams,
    ResolvePositionsResponse,
    ResolvedPositionInfo,
    ResolvePositionsSuggestion,
)
from src.http.discovery_client import DiscoveryApiClient
from src.utils.normalizer import normalize_positions
from src.utils.validator import validate_autocomplete_params, validate_resolve_params


class LocationService:

    def __init__(self, client: DiscoveryApiClient | None = None):
        self.client = client or DiscoveryApiClient()
        logger.info(f"[LocationService] Initialized with client: {type(self.client).__name__}")

    async def positions_autocomplete(self, params: AutocompleteParams) -> AutocompleteResponse:
        """Handles autocomplete suggestions for user-entered location terms."""
        logger.info(f"[Autocomplete] Received term='{params.term}', locale='{params.locale}', limit={params.limit}")

        try:
            validate_autocomplete_params(params)
            logger.debug("[Autocomplete] Parameters validation passed")
        except Exception as e:
            logger.error(f"[Autocomplete] Parameters validation failed: {e}")
            raise

        endpoint = settings.POSITION_ENDPOINT
        logger.debug(f"[Autocomplete] Using endpoint: {endpoint}")

        request_params = {
            "term": params.term,
            "locale": params.locale,
            "limit": params.limit,
        }
        logger.debug(f"[Autocomplete] API request params: {request_params}")

        try:
            raw = await self.client.get(endpoint, params=request_params)
            logger.debug(f"[Autocomplete] API response received, type: {type(raw)}")
        except Exception as e:
            logger.error(f"[Autocomplete] API request failed: {e}", exc_info=True)
            raise

        if isinstance(raw, dict):
            logger.debug(f"[Autocomplete] Response is dict with keys: {list(raw.keys())}")
            for key, value in raw.items():
                if isinstance(value, list):
                    logger.debug(f"[Autocomplete] Key '{key}' contains list with {len(value)} items")
        elif isinstance(raw, list):
            logger.debug(f"[Autocomplete] Response is list with {len(raw)} items")
        else:
            logger.warning(f"[Autocomplete] Unexpected response type: {type(raw)}")

        raw_str = str(raw)[:500]
        logger.debug(f"[Autocomplete] Raw response preview: {raw_str}...")

        if isinstance(raw, list):
            positions_data = raw
            logger.debug(f"[Autocomplete] Using raw list directly: {len(positions_data)} items")
        elif isinstance(raw, dict):
            positions_data = (
                    raw.get("positions") or
                    raw.get("results") or
                    raw.get("data") or
                    raw.get("items") or
                    raw.get("locations") or
                    []
            )
            logger.debug(f"[Autocomplete] Extracted {len(positions_data)} items from dict")

            if not positions_data and raw:
                logger.warning(
                    f"[Autocomplete] Could not find positions in response. "
                    f"Available keys: {list(raw.keys())}"
                )
        else:
            positions_data = []
            logger.error(f"[Autocomplete] Cannot extract positions from type: {type(raw)}")

        logger.debug(f"[Autocomplete] Normalizing {len(positions_data)} raw positions")
        candidates = normalize_positions(positions_data)
        logger.info(f"[Autocomplete] Retrieved {len(candidates)} candidates for term '{params.term}'")

        logger.debug("[Autocomplete] Searching for best match (type='location')")
        best_guess = next(
            (p for p in candidates if p.type == "location"),
            candidates[0] if candidates else None,
        )

        alternatives = [
            p for p in candidates
            if not best_guess or p.id != best_guess.id
        ]
        logger.debug(f"[Autocomplete] Found {len(alternatives)} alternative positions")

        if best_guess:
            logger.info(
                f"[Autocomplete] Best match: id={best_guess.id}, name='{best_guess.name}', "
                f"type={best_guess.type}, country={best_guess.country_code}"
            )
        else:
            logger.warning(f"[Autocomplete] No valid match found for term '{params.term}'")

        response = AutocompleteResponse(best_guess=best_guess, alternatives=alternatives)
        logger.debug(f"[Autocomplete] Returning response with {len(response.alternatives)} alternatives")

        return response

    async def resolve_positions(self, params: ResolvePositionsParams) -> ResolvePositionsResponse:
        """
        Resolves both origin and destination positions by calling positions_autocomplete.
        """
        logger.info(
            f"[Resolve] Resolving positions for from='{params.from_term}' → to='{params.to_term}', "
            f"locale='{params.locale}', limit_each={params.limit_each}"
        )

        try:
            validate_resolve_params(params)
            logger.debug("[Resolve] Parameters validation passed")
        except Exception as e:
            logger.error(f"[Resolve] Parameters validation failed: {e}")
            raise

        logger.debug(f"[Resolve] Step 1/2: Resolving origin '{params.from_term}'")
        try:
            origin_autocomplete = await self.positions_autocomplete(
                type('Obj', (), {
                    'term': params.from_term,
                    'locale': params.locale,
                    'limit': params.limit_each
                })()
            )
            logger.debug(
                f"[Resolve] Origin autocomplete returned: "
                f"best_guess={origin_autocomplete.best_guess.name if origin_autocomplete.best_guess else None}, "
                f"alternatives={len(origin_autocomplete.alternatives)}"
            )
        except Exception as e:
            logger.error(f"[Resolve] Failed to autocomplete origin '{params.from_term}': {e}", exc_info=True)
            raise

        origin_candidates = (
                                [origin_autocomplete.best_guess] if origin_autocomplete.best_guess else []
                            ) + origin_autocomplete.alternatives

        logger.debug(f"[Resolve] Total origin candidates: {len(origin_candidates)}")

        origin_best = next(
            (p for p in origin_candidates if p.type == "location"),
            origin_candidates[0] if origin_candidates else None,
        )

        if origin_best:
            logger.debug(f"[Resolve] Selected origin: id={origin_best.id}, name='{origin_best.name}'")
        else:
            logger.warning(f"[Resolve] No suitable origin found for '{params.from_term}'")

        logger.debug(f"[Resolve] Step 2/2: Resolving destination '{params.to_term}'")
        try:
            dest_autocomplete = await self.positions_autocomplete(
                type('Obj', (), {
                    'term': params.to_term,
                    'locale': params.locale,
                    'limit': params.limit_each
                })()
            )
            logger.debug(
                f"[Resolve] Destination autocomplete returned: "
                f"best_guess={dest_autocomplete.best_guess.name if dest_autocomplete.best_guess else None}, "
                f"alternatives={len(dest_autocomplete.alternatives)}"
            )
        except Exception as e:
            logger.error(f"[Resolve] Failed to autocomplete destination '{params.to_term}': {e}", exc_info=True)
            raise

        dest_candidates = (
                              [dest_autocomplete.best_guess] if dest_autocomplete.best_guess else []
                          ) + dest_autocomplete.alternatives

        logger.debug(f"[Resolve] Total destination candidates: {len(dest_candidates)}")

        dest_best = next(
            (p for p in dest_candidates if p.type == "location"),
            dest_candidates[0] if dest_candidates else None,
        )

        if dest_best:
            logger.debug(f"[Resolve] Selected destination: id={dest_best.id}, name='{dest_best.name}'")
        else:
            logger.warning(f"[Resolve] No suitable destination found for '{params.to_term}'")

        if origin_best and dest_best:
            logger.info(
                f"[Resolve] ✅ Successfully resolved: "
                f"origin='{origin_best.name}' (id={origin_best.id}) → "
                f"destination='{dest_best.name}' (id={dest_best.id})"
            )
        else:
            logger.error(
                f"[Resolve] ❌ Resolution failed: "
                f"origin={'✓' if origin_best else '✗'} ('{params.from_term}'), "
                f"destination={'✓' if dest_best else '✗'} ('{params.to_term}')"
            )

        response = ResolvePositionsResponse(
            origin=ResolvedPositionInfo(
                user_term=params.from_term,
                best_match=origin_best,
                ranked_candidates=origin_candidates,
            ),
            destination=ResolvedPositionInfo(
                user_term=params.to_term,
                best_match=dest_best,
                ranked_candidates=dest_candidates,
            ),
            suggestion=ResolvePositionsSuggestion(
                from_id=origin_best.id if origin_best else None,
                to_id=dest_best.id if dest_best else None,
            ),
        )

        logger.debug(
            f"[Resolve] Returning response: "
            f"origin_candidates={len(origin_candidates)}, "
            f"dest_candidates={len(dest_candidates)}, "
            f"suggestion=({response.suggestion.from_id}, {response.suggestion.to_id})"
        )

        return response