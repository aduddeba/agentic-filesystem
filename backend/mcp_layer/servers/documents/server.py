"""Document MCP server -- text extraction, chunking, and metadata for indexed files."""

from mcp.server.fastmcp import FastMCP

from .. import _runtime
from . import impl

mcp = FastMCP("documents", port=8803)


@mcp.tool(name="document.extract_text")
def extract_text(path: str) -> impl.ExtractTextOut:
    """Extract plain text from a file relative to the storage root (PDF/DOCX/XLSX parsed, else UTF-8)."""
    return impl.extract_text(path)


@mcp.tool(name="document.chunk")
def chunk(text: str, chunk_size: int = 200, overlap: int = 40) -> impl.ChunkResultOut:
    """Split `text` into overlapping word-based chunks for embedding."""
    return impl.chunk(text, chunk_size=chunk_size, overlap=overlap)


@mcp.tool(name="document.metadata")
def metadata(path: str, text: str) -> impl.MetadataOut:
    """Guess the MIME type from `path` and count words/characters in `text`."""
    return impl.metadata(path, text)


app = _runtime.build_app(mcp)

if __name__ == "__main__":
    _runtime.run_main(mcp)
