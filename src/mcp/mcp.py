from fastmcp import FastMCP

from src.auth.auth import auth_provider
from src.mcp.tools.resolve_tools import resolve_mcp
from src.mcp.tools.search_tools import search_mcp

mcp_router = FastMCP("Main MCP", auth=auth_provider)

mcp_router.mount(resolve_mcp)
mcp_router.mount(search_mcp)
