from src.core.logger import logger
from typing import List, Dict, Any, Tuple
from src.schemas.models import Position, BaseSearchParams, Itinerary, TimeInfo


def normalize_positions(raw_positions: List[Dict[str, Any]]) -> List[Position]:

    logger.debug(f"[Normalizer1] normalize_positions called with {len(raw_positions)} raw positions")

    if not raw_positions:
        logger.warning("[Normalizer1] Empty raw_positions list received")
        return []

    if raw_positions:
        logger.debug(f"[Normalizer1] First raw position sample: {raw_positions[0]}")

    positions = []
    skipped_count = 0

    for idx, pos in enumerate(raw_positions):
        if not pos:
            logger.debug(f"[Normalizer1] Skipping empty position at index {idx}")
            skipped_count += 1
            continue

        if "positionId" not in pos:
            logger.debug(
                f"[Normalizer1] Skipping position at index {idx}: missing 'positionId'. Keys: {list(pos.keys())}")
            skipped_count += 1
            continue

        name = pos.get('displayName') or pos.get('defaultName') or pos.get('name')

        if not name:
            logger.debug(
                f"[Normalizer1] Skipping position at index {idx}: no name field found. "
                f"Keys: {list(pos.keys())}"
            )
            skipped_count += 1
            continue

        try:
            position_id = int(pos["positionId"])
        except (TypeError, ValueError) as e:
            logger.warning(
                f"[Normalizer1] Invalid positionId at index {idx}: '{pos.get('positionId')}' "
                f"(type: {type(pos.get('positionId'))}). Error: {e}"
            )
            skipped_count += 1
            continue

        position_type = pos.get("type", "unknown")

        country_code = pos.get("countryCode")

        logger.debug(
            f"[Normalizer1] Position {idx}: id={position_id}, name='{name}', "
            f"type={position_type}, country={country_code}"
        )

        positions.append(
            Position(
                id=position_id,
                name=name,
                type=position_type,
                countryCode=country_code,
            )
        )

    logger.info(
        f"[Normalizer1] Normalized {len(positions)} positions (skipped {skipped_count} invalid entries)"
    )

    return positions


def prepare_common_api_params(params: BaseSearchParams, from_id: int, to_id: int) -> Dict[str, Any]:

    logger.debug(f"[Normalizer2] Preparing API params: from_id={from_id}, to_id={to_id}")
    logger.debug(f"[Normalizer2] Input params: {params.model_dump()}")

    if isinstance(params.modes, list):
        modes_str = ",".join(params.modes)
        logger.debug(f"[Normalizer2] Converted modes list {params.modes} to string '{modes_str}'")
    else:
        modes_str = params.modes
        logger.debug(f"[Normalizer2] Using modes as-is: '{modes_str}'")

    api_params = {
        "fromId": from_id,
        "toId": to_id,
        "adults": str(params.adults),
        "children": str(params.children),
        "infants": str(params.infants),
        "travelModes": modes_str,
        "locale": params.locale,
        "currency": params.currency,
    }

    logger.debug(f"[Normalizer2] Prepared API params: {api_params}")

    return api_params


def shape_day_results(raw_data: Dict[str, Any]) -> List[Itinerary]:
    logger.debug("[Normalizer3] shape_day_results called")

    carriers_map = {str(c.get("id")): c.get("name") or c.get("code") or str(c.get("id"))
                    for c in raw_data.get("carriers", [])}
    positions_map = {str(p.get("id")): p.get("name") or str(p.get("id"))
                     for p in raw_data.get("positions", [])}
    segments_map = {str(s.get("id")): s for s in raw_data.get("segments", [])}

    schedule_keys = ["combinedSchedules", "outboundSchedules", "inboundSchedules"]
    all_schedules = []
    for key in schedule_keys:
        schedules = raw_data.get(key, []) or []
        all_schedules.extend(schedules)

    shaped_results: List[Itinerary] = []
    errors_count = 0

    for idx, sched in enumerate(all_schedules):
        try:
            if not isinstance(sched, dict):
                logger.warning(f"[Normalizer3] Itinerary {idx} skipped: expected dict, got {type(sched)}")
                errors_count += 1
                continue

            segment_ids = [str(sid) for sid in sched.get("segmentIDs") or [] if sid in segments_map]
            segments_data = [segments_map[sid] for sid in segment_ids]
            segments_data.sort(key=lambda s: s.get("departureDateTime") or "")

            first_seg = segments_data[0] if segments_data else {}

            dep_info = first_seg.get("departureDateTime") or sched.get("departureAt")
            arr_info = first_seg.get("arrivalDateTime") or sched.get("arrivalAt")

            dep_tz = first_seg.get("departureTimeZone") or "UTC"
            arr_tz = first_seg.get("arrivalTimeZone") or "UTC"

            dep = TimeInfo(datetime=dep_info, tz=dep_tz)
            arr = TimeInfo(datetime=arr_info, tz=arr_tz)

            from_pos_id = str(first_seg.get("departurePositionId") or raw_data.get("fromPosId") or "")
            to_pos_id = str(first_seg.get("arrivalPositionId") or raw_data.get("toPosId") or "")

            itinerary = Itinerary(
                from_term=positions_map.get(from_pos_id, "Unknown"),
                to_term=positions_map.get(to_pos_id, "Unknown"),
                mode=first_seg.get("travelMode") or sched.get("travelMode") or "unknown",
                stableId=str(sched.get("id") or first_seg.get("id") or ""),
                priceFrom=float(sched.get("priceCents", 0)) / 100,
                currency=sched.get("currency") or "EUR",
                duration=str(first_seg.get("durationMinutes") or sched.get("duration") or 0),
                departure=dep,
                arrival=arr,
                carrier=carriers_map.get(str(first_seg.get("carrierId"))) if first_seg.get("carrierId") else None,
            )

            shaped_results.append(itinerary)

            logger.debug(
                f"[Normalizer3] Itinerary {idx} processed: {itinerary.from_term} → {itinerary.to_term}, "
                f"mode={itinerary.mode}, price={itinerary.priceFrom} {itinerary.currency}"
            )

        except Exception as e:
            errors_count += 1
            logger.error(f"[Normalizer3] Failed to process itinerary {idx}: {e}", exc_info=True)
            logger.debug(f"[Normalizer3] Problematic schedule data: {sched}")
            continue

    logger.info(f"[Normalizer3] Shaped {len(shaped_results)} itineraries ({errors_count} errors)")
    return shaped_results


def normalize_calendar_day_results(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Нормализует данные календаря цен из API"""

    logger.debug("[Normalizer] normalize_calendar_day_results called")
    logger.debug(f"[Normalizer] Input data keys: {list(data.keys())}")

    # Извлекаем основные параметры из ответа
    request_id = data.get("requestId")
    from_pos_id = data.get("fromPosId")
    to_pos_id = data.get("toPosId")
    currency = data.get("currency", "EUR")

    logger.info(
        f"[Normalizer] Calendar request: requestId={request_id}, "
        f"from={from_pos_id}, to={to_pos_id}, currency={currency}"
    )

    # API возвращает 'prices', а не 'calendar'
    price_days: List[Dict[str, Any]] = data.get("prices", [])

    if not price_days:
        logger.warning("[Normalizer] No prices found in API response")
        return {
            "requestId": request_id,
            "fromPosId": from_pos_id,
            "toPosId": to_pos_id,
            "currency": currency,
            "calendar": [],
        }, 0

    logger.debug(f"[Normalizer] Processing {len(price_days)} price entries")

    normalized_days = []
    min_price_cents = None
    max_price_cents = None

    for idx, day in enumerate(price_days):
        date = day.get("date")
        price_cents = day.get("priceCents")

        if date is None or price_cents is None:
            logger.warning(f"[Normalizer] Skipping day {idx}: missing date or priceCents")
            continue

        # Отслеживаем min/max цены
        if min_price_cents is None or price_cents < min_price_cents:
            min_price_cents = price_cents
        if max_price_cents is None or price_cents > max_price_cents:
            max_price_cents = price_cents

        # Модель CalendarDay ожидает priceCents (float), date и currency
        normalized_day = {
            "date": date,
            "priceCents": float(price_cents),  # конвертируем в float
            "currency": currency,
        }

        normalized_days.append(normalized_day)

        logger.debug(
            f"[Normalizer] Day {idx}: {date} → {price_cents} cents "
            f"({float(price_cents) / 100:.2f} {currency})"
        )

    result = {
        "requestId": request_id,
        "fromPosId": from_pos_id,
        "toPosId": to_pos_id,
        "currency": currency,
        "calendar": normalized_days,
        "stats": {
            "min_price_cents": min_price_cents,
            "max_price_cents": max_price_cents,
            "min_price": float(min_price_cents) / 100 if min_price_cents else None,
            "max_price": float(max_price_cents) / 100 if max_price_cents else None,
            "total_days": len(normalized_days),
        }
    }

    logger.info(
        f"[Normalizer] Normalized {len(normalized_days)} calendar days. "
        f"Price range: {result['stats']['min_price']:.2f} - {result['stats']['max_price']:.2f} {currency}"
    )

    return result, len(normalized_days)


def normalize_cheapest_summary_results(
        data: Dict[str, Any],
        currency: str = "EUR"
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Нормализует данные о самых дешевых ценах по датам и типам транспорта.

    Args:
        data: Сырой ответ от API с данными о ценах
        currency: Валюта (по умолчанию EUR)

    Returns:
        Tuple[Dict, Dict]: (нормализованные данные, статистика)
    """

    logger.debug("[Normalizer] normalize_cheapest_summary_results called")
    logger.debug(f"[Normalizer] Input data keys: {list(data.keys())}")

    # Извлекаем основные данные
    price_data = data.get("data", {})
    errors = data.get("errors")

    if errors:
        logger.warning(f"[Normalizer] API returned errors: {errors}")

    if not price_data:
        logger.warning("[Normalizer] No price data found in API response")
        return {
            "summary": {},
            "currency": currency,
            "errors": errors,
        }, {"total_dates": 0, "total_modes": 0, "total_results": 0}

    logger.info(f"[Normalizer] Processing {len(price_data)} dates")

    # Структура для результата: {date: {mode: CheapestPriceInfo}}
    summary_by_date = {}

    # Статистика
    stats = {
        "total_dates": 0,
        "total_modes": 0,
        "total_results": 0,
        "by_mode": {},  # подсчет по каждому виду транспорта
        "min_price_overall": None,
        "max_price_overall": None,
        "cheapest_date": None,
        "cheapest_mode": None,
    }

    for date, modes_data in price_data.items():
        if not isinstance(modes_data, dict):
            logger.warning(f"[Normalizer] Invalid data format for date {date}")
            continue

        stats["total_dates"] += 1
        date_prices = {}

        for mode, price_info in modes_data.items():
            if not isinstance(price_info, dict):
                continue

            price_cents = price_info.get("priceCents", 0)
            num_results = price_info.get("numberOfResults", 0)
            last_updated = price_info.get("lastUpdatedAt")

            # Пропускаем записи без цен или результатов
            if price_cents == 0 or num_results == 0:
                logger.debug(f"[Normalizer] Skipping {date} - {mode}: no prices/results")
                continue

            # Конвертируем центы в основную валюту
            min_price = float(price_cents) / 100

            # Обновляем статистику
            stats["total_modes"] += 1
            stats["total_results"] += num_results

            if mode not in stats["by_mode"]:
                stats["by_mode"][mode] = {
                    "count": 0,
                    "total_results": 0,
                    "min_price": None,
                    "max_price": None,
                }

            stats["by_mode"][mode]["count"] += 1
            stats["by_mode"][mode]["total_results"] += num_results

            # Обновляем min/max для режима
            mode_stats = stats["by_mode"][mode]
            if mode_stats["min_price"] is None or min_price < mode_stats["min_price"]:
                mode_stats["min_price"] = min_price
            if mode_stats["max_price"] is None or min_price > mode_stats["max_price"]:
                mode_stats["max_price"] = min_price

            # Обновляем общие min/max
            if stats["min_price_overall"] is None or min_price < stats["min_price_overall"]:
                stats["min_price_overall"] = min_price
                stats["cheapest_date"] = date
                stats["cheapest_mode"] = mode

            if stats["max_price_overall"] is None or min_price > stats["max_price_overall"]:
                stats["max_price_overall"] = min_price

            # Добавляем в результат
            date_prices[mode] = {
                "min_price": min_price,
                "price_cents": price_cents,
                "currency": currency,
                "number_of_results": num_results,
                "last_updated_at": last_updated,
            }

            logger.debug(
                f"[Normalizer] {date} - {mode}: {min_price:.2f} {currency} "
                f"({num_results} results)"
            )

        if date_prices:
            summary_by_date[date] = date_prices

    result = {
        "summary": summary_by_date,
        "currency": currency,
        "errors": errors,
        "stats": stats,
    }

    logger.info(
        f"[Normalizer] Normalized {stats['total_dates']} dates with "
        f"{stats['total_modes']} transport modes. "
        f"Price range: {stats['min_price_overall']:.2f} - {stats['max_price_overall']:.2f} {currency}"
    )

    if stats["cheapest_date"] and stats["cheapest_mode"]:
        logger.info(
            f"[Normalizer] Cheapest option: {stats['cheapest_date']} via {stats['cheapest_mode']} "
            f"at {stats['min_price_overall']:.2f} {currency}"
        )

    return result, stats


def normalize_fastest_summary_results(
        data: Dict[str, Any],
        currency: str = "EUR"
) -> Dict[str, Any]:
    """
    Нормализует данные о самых быстрых и дешевых вариантах.
    Простой парсинг без форматирования и статистики.

    Args:
        data: Сырой ответ от API
        currency: Валюта (по умолчанию EUR)

    Returns:
        Dict: нормализованные данные
    """

    logger.debug("[Normalizer] normalize_fastest_summary_results called")

    # Извлекаем основные данные
    price_data = data.get("data", {})

    if not price_data:
        logger.warning("[Normalizer] No price data found in API response")
        return {"summary": {}, "currency": currency}

    logger.debug(f"[Normalizer] Processing {len(price_data)} dates")

    # Структура для результата: {date: {mode: info}}
    summary_by_date = {}

    for date, modes_data in price_data.items():
        if not isinstance(modes_data, dict):
            continue

        date_summary = {}

        for mode, mode_info in modes_data.items():
            if not isinstance(mode_info, dict):
                continue

            num_results = mode_info.get("numberOfResults", 0)

            # Пропускаем записи без результатов
            if num_results == 0:
                continue

            cheapest_info = mode_info.get("cheapest", {})
            fastest_info = mode_info.get("fastest", {})

            cheapest_price_cents = cheapest_info.get("priceCents", 0)
            cheapest_duration_min = cheapest_info.get("durationMinutes", 0)

            fastest_price_cents = fastest_info.get("priceCents", 0)
            fastest_duration_min = fastest_info.get("durationMinutes", 0)

            # Пропускаем если нет данных
            if cheapest_price_cents == 0 and fastest_price_cents == 0:
                continue

            # Конвертируем центы в основную валюту
            cheapest_price = float(cheapest_price_cents) / 100 if cheapest_price_cents > 0 else None
            fastest_price = float(fastest_price_cents) / 100 if fastest_price_cents > 0 else None

            # Добавляем в результат без форматирования
            date_summary[mode] = {
                "fastest_duration": str(fastest_duration_min),
                "fastest_price": fastest_price if fastest_price else 0.0,
                "cheapest_price": cheapest_price if cheapest_price else None,
                "currency": currency,
            }

            logger.debug(
                f"[Normalizer] {date} - {mode}: "
                f"fastest={fastest_duration_min}min @ {fastest_price if fastest_price else 0:.2f}, "
                f"cheapest={cheapest_price if cheapest_price else 0:.2f}"
            )

        if date_summary:
            summary_by_date[date] = date_summary

    logger.info(f"[Normalizer] Normalized {len(summary_by_date)} dates")

    return {
        "summary": summary_by_date,
        "currency": currency,
    }