"""Implementation behind the Search MCP server -- wraps `tools/filesystem/search.py` (ripgrep,
with a pure-Python fallback), jailed to the storage root like the Filesystem server."""

from pathlib import Path
from typing import TypedDict

from app.paths import resolve_path, to_relative
from tools.filesystem import search as search_tool


class SearchMatchOut(TypedDict):
    path: str
    line: int
    text: str


class SearchOut(TypedDict):
    matches: list[SearchMatchOut]


def keyword(query: str, path: str = "") -> SearchOut:
    """Search for `query` across files under a path relative to the storage root."""
    if not query.strip():
        return SearchOut(matches=[])

    root = resolve_path(path)
    matches = search_tool(query, root=str(root))
    return SearchOut(
        matches=[
            SearchMatchOut(path=to_relative(Path(m.file)), line=m.line, text=m.text) for m in matches
        ]
    )
