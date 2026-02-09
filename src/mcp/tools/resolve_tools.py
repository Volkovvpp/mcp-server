from fastmcp import FastMCP
from src.factory.singleton_factory import get_location_service, get_search_service
from src.schemas import models
from src.core.logger import logger
from src.utils.metrics import trace_tool

resolve_mcp = FastMCP("Resolve MCP")

location_service = get_location_service()
search_service = get_search_service()


@resolve_mcp.tool()
@trace_tool
async def resolve_positions(params: models.ResolvePositionsParams):
    """
    Resolves free-text origin and destination terms into unique position IDs {fromId, toId}
    required for ticket search tools.

    Input parameters:
    - from_term: the name of the origin location (string)
    - to_term: the name of the destination location (string)
    - locale: search locale (default is "en")
    - limit_each: number of candidate positions to fetch per term (default is 20)

    Returns:
    - origin and destination: best match and ranked candidate positions
    - suggestion: recommended from_id and to_id for subsequent searches

    Possible errors:
    - bad_input: if required fields are missing or invalid
    - upstream_unavailable: if the Discovery API is unavailable
    """
    logger.info(f"[MCP TOOL] resolve_positions called")
    result = await location_service.resolve_positions(params)
    return result.model_dump()