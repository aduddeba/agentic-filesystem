"""Embedding MCP server -- sentence-transformers, kept warm across calls."""

from mcp.server.fastmcp import FastMCP

from .. import _runtime
from . import impl

mcp = FastMCP("embeddings", port=8804)


@mcp.tool(name="embedding.generate")
def generate(texts: list[str]) -> impl.GenerateOut:
    """Embed a batch of passage/document texts."""
    return impl.generate(texts)


@mcp.tool(name="embedding.query")
def query(text: str) -> impl.QueryOut:
    """Embed a search query, applying BGE's asymmetric retrieval instruction prefix."""
    return impl.query(text)


app = _runtime.build_app(mcp)

if __name__ == "__main__":
    _runtime.run_main(mcp)
