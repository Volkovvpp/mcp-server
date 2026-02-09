from fastmcp import FastMCP
from src.factory.singleton_factory import get_search_service, get_location_service
from src.schemas import models
from src.core.logger import logger
from src.utils.metrics import trace_tool

search_mcp = FastMCP("Search MCP")

location_service = get_location_service()
search_service = get_search_service()


@search_mcp.tool()
@trace_tool
async def search_day_results(params: models.SearchDayResultsParams):
    """
    Retrieve normalized single-day travel schedules.

    Use this tool when you want schedules for a specific outbound date, with
    an optional return date. The tool accepts either free-text location names
    (`from_term`, `to_term`) or numeric IDs (`from_id`, `to_id`).

    Input parameters:
    - from_term / from_id: origin location (text or numeric ID)
    - to_term / to_id: destination location (text or numeric ID)
    - date_out: departure date (YYYY-MM-DD)
    - date_return: optional return date (YYYY-MM-DD) for round trips
    - travelModes: list of transport modes to include (default: ["bus", "train", "flight"])
    - locale: language code for localization (default: "en")
    - currency: target currency for price display (default: "EUR")

    Returns:
    - results: list of available itineraries with duration, price, and carrier information
    - note: optional hints about local timezones or estimated prices linkage

    Possible errors:
    - bad_input: missing or malformed fields
    - upstream_unavailable: if the upstream Discovery API fails to return results
    - no_results: if no matching itineraries were found
    """
    logger.info(f"[MCP TOOL] search_day_results called")
    result = await search_service.search_day_results(params)
    return result.model_dump()



@search_mcp.tool()
@trace_tool
async def search_calendar_prices(params: models.SearchCalendarPricesParams):
    """
    Fetch the lowest fares for a date-range calendar view (≤31 days).

    Use when you need minimum available prices for each day in a window.
    Accepts either text-based locations (`from_term`, `to_term`) or numeric
    IDs (`from_id`, `to_id`).

    Input parameters:
    - from_term / to_term: free-text names of the origin and destination (alternatively use from_id / to_id)
    - date_start: start date of the search range (YYYY-MM-DD)
    - date_end: end date of the search range (YYYY-MM-DD)
    - locale, currency: optional parameters to adjust results to a specific region or currency

    Returns:
    - journey_type: ONE_WAY or ROUND_TRIP (auto-detected if not specified)
    - A list of days with the lowest available prices for each date.
    - Each entry includes the date, minimum price, and optionally the travel mode.

    Use cases:
    - Displaying a price calendar to help users choose the cheapest travel dates.
    - Supporting flexible date searches.

    Possible errors:
    - bad_input: if date range or location parameters are invalid
    - range_exceeded: if the date range exceeds the 31-day limit
    - upstream_unavailable: if the pricing API or data source is unavailable
    """
    logger.info(f"[MCP TOOL] search_calendar_prices called with {params.model_dump()}")
    result = await search_service.search_calendar_prices(params)
    return result.model_dump()


@search_mcp.tool()
@trace_tool
async def search_cheapest_summary(params: models.SearchSummaryParams):
    """
    Summarize the lowest fares per travel mode across a date window (≤30 days).

    Use this tool to compare which mode (train, bus, flight) is cheapest
    over a multi-day period. Accepts either free-text or numeric location
    identifiers.

    Input parameters:
    - from_term / to_term: free-text names of the origin and destination (or from_id / to_id)
    - date_start: start date of the search range (YYYY-MM-DD)
    - date_end: end date of the search range (YYYY-MM-DD)
    - locale, currency: optional parameters to localize results

    Returns:
    - A summary of the lowest average prices per transport mode.
    - Each entry includes the mode, average price, and available dates with the cheapest fares.

    Use cases:
    - Comparing which transport mode offers the best prices over time.
    - Displaying summarized results for flexible or multi-modal travel planning.

    Possible errors:
    - bad_input: if required fields or date range are invalid
    - range_exceeded: if the date range exceeds 30 days
    - upstream_unavailable: if the search or pricing API is unavailable
    """
    logger.info(f"[MCP TOOL] search_cheapest_summary called with {params.model_dump()}")
    result = await search_service.search_cheapest_summary(params)
    return result.model_dump()



@search_mcp.tool()
@trace_tool
async def search_fastest_summary(params: models.SearchSummaryParams):
    """
    Summarize the fastest itineraries per travel mode across a date window.

    Inputs mirror `search_cheapest_summary`: date range ≤30 days, allowed
    travel modes, and optional locale/currency. Use this tool when duration
    matters more than price.

    Input parameters:
    - from_term / to_term: free-text names of the origin and destination (or from_id / to_id)
    - date_start: start date of the comparison window (YYYY-MM-DD)
    - date_end: end date of the comparison window (YYYY-MM-DD)
    - locale, currency: optional parameters for localized output

    Returns:
    - For each day, the fastest and cheapest itineraries per transport mode.
    - Includes key metrics such as duration, price, and departure/arrival times.
    - Identifies the globally fastest option across all modes and dates.

    Use cases:
    - Comparing time vs. cost efficiency between transport modes.
    - Recommending the best overall travel option based on user priorities.

    Possible errors:
    - bad_input: if required fields or date range are invalid
    - range_exceeded: if the date range exceeds 30 days
    - upstream_unavailable: if the travel data source or API is unavailable
    """
    logger.info(f"[MCP TOOL] search_fastest_summary called with {params.model_dump()}")
    result = await search_service.search_fastest_summary(params)
    return result.model_dump()