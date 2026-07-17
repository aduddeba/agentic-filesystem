"""Implementation behind the Document MCP server -- wraps `tools/documents/*` for chunking and
metadata, plus `tools/filesystem/read.py`'s multi-format text extraction (PDF/DOCX/XLSX/plain)."""

from typing import TypedDict

from app.paths import resolve_path
from tools.documents import chunk_text, extract_metadata
from tools.filesystem import read as read_tool


class ExtractTextOut(TypedDict):
    path: str
    content: str


def extract_text(path: str) -> ExtractTextOut:
    """Extract plain text from a file relative to the storage root (PDF/DOCX/XLSX parsed, else UTF-8)."""
    target = resolve_path(path)
    return ExtractTextOut(path=path, content=read_tool(str(target)))


class ChunkOut(TypedDict):
    index: int
    text: str


class ChunkResultOut(TypedDict):
    chunks: list[ChunkOut]


def chunk(text: str, chunk_size: int = 200, overlap: int = 40) -> ChunkResultOut:
    """Split `text` into overlapping word-based chunks for embedding."""
    pieces = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    return ChunkResultOut(chunks=[ChunkOut(index=p.index, text=p.text) for p in pieces])


class MetadataOut(TypedDict):
    mime_type: str | None
    word_count: int
    char_count: int


def metadata(path: str, text: str) -> MetadataOut:
    """Guess the MIME type from `path` and count words/characters in `text`."""
    meta = extract_metadata(path, text)
    return MetadataOut(mime_type=meta.mime_type, word_count=meta.word_count, char_count=meta.char_count)
