"""Search for a text query across files under a directory."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchMatch:
    file: str
    line: int
    text: str


def search(query: str, root: str = ".") -> list[SearchMatch]:
    """Search for `query` across files under `root`.

    Uses ripgrep when available for speed; falls back to a pure-Python
    walk otherwise so this works without any external binary installed.
    Files whose *name* matches `query` are also included (even if the query
    never appears in their content), so a query like "README" surfaces
    README.md even though the word "README" isn't written anywhere inside it.
    """
    if not query.strip():
        return []

    rg_path = shutil.which("rg")
    matches = _search_ripgrep(rg_path, query, root) if rg_path is not None else _search_python(query, root)
    matches.extend(_filename_matches(query, root, exclude={m.file for m in matches}))
    return matches


def _search_ripgrep(rg_path: str, query: str, root: str) -> list[SearchMatch]:
    result = subprocess.run(
        [rg_path, "--json", query, root],
        capture_output=True,
        text=True,
    )

    matches = []
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        matches.append(
            SearchMatch(
                file=data["path"]["text"],
                line=data["line_number"],
                text=data["lines"]["text"].rstrip("\n"),
            )
        )
    return matches


def _filename_matches(query: str, root: str, exclude: set[str]) -> list[SearchMatch]:
    """Files under `root` whose name contains `query`, skipping files already in `exclude`."""
    query_lower = query.lower()
    matches = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or query_lower not in path.name.lower():
            continue
        path_str = str(path)
        if path_str in exclude:
            continue
        matches.append(SearchMatch(file=path_str, line=1, text=path.name))
    return matches


def _search_python(query: str, root: str) -> list[SearchMatch]:
    matches = []
    query_lower = query.lower()
    for path in Path(root).rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (UnicodeDecodeError, PermissionError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query_lower in line.lower():
                matches.append(
                    SearchMatch(file=str(path), line=line_number, text=line)
                )
    return matches
