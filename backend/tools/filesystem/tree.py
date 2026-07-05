"""Walk a directory tree in display order."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TreeEntry:
    path: str
    name: str
    is_dir: bool
    depth: int
    size: int


def walk(root: str) -> list[TreeEntry]:
    """Walk `root`, returning a flattened, depth-first listing of its contents.

    Folders are listed before files within each directory, both sorted
    alphabetically (case-insensitive). The root itself is not included.
    Returns an empty list if `root` does not exist or is not a directory.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return []
    return _walk(root_path, root_path, depth=0)


def _walk(root_path: Path, dir_path: Path, depth: int) -> list[TreeEntry]:
    entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    result: list[TreeEntry] = []
    for entry in entries:
        rel = entry.relative_to(root_path).as_posix()
        if entry.is_dir():
            result.append(TreeEntry(path=rel, name=entry.name, is_dir=True, depth=depth, size=0))
            result.extend(_walk(root_path, entry, depth + 1))
        else:
            result.append(
                TreeEntry(path=rel, name=entry.name, is_dir=False, depth=depth, size=entry.stat().st_size)
            )
    return result
