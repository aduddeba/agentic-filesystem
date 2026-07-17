"""Vector MCP server -- hybrid keyword+vector semantic search, and chunk CRUD, over pgvector."""

from typing import Literal

from mcp.server.fastmcp import FastMCP

from .. import _runtime
from . import impl

mcp = FastMCP("vectors", port=8805)


@mcp.tool(name="semantic.search")
def search(query: str, k: int = 10, mode: Literal["hybrid", "vector"] = "hybrid") -> impl.SearchOut:
    """Rank indexed file chunks by embedding similarity to `query`, optionally fused with keyword search."""
    return impl.search(query, k=k, mode=mode)


@mcp.tool(name="semantic.insert")
def insert(file_path: str, chunk_index: int, text: str) -> impl.InsertOut:
    """Embed `text` and store it as a chunk of the already-indexed file at `file_path`."""
    return impl.insert(file_path, chunk_index, text)


@mcp.tool(name="semantic.delete")
def delete(file_path: str) -> impl.DeleteOut:
    """Delete every chunk belonging to the file at `file_path`."""
    return impl.delete(file_path)


app = _runtime.build_app(mcp)

if __name__ == "__main__":
    _runtime.run_main(mcp)
