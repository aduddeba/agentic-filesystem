"""Search MCP server -- keyword search over file contents under the storage root."""

from mcp.server.fastmcp import FastMCP

from .. import _runtime
from . import impl

mcp = FastMCP("search", port=8802)


@mcp.tool(name="search.keyword")
def keyword(query: str, path: str = "") -> impl.SearchOut:
    """Search for `query` across files under a path relative to the storage root."""
    return impl.keyword(query, path)


app = _runtime.build_app(mcp)

if __name__ == "__main__":
    _runtime.run_main(mcp)
