"""Implementation behind the Filesystem MCP server -- wraps `tools/filesystem/*`.

Every path argument is resolved through `app.paths.resolve_path()` before it
reaches a `tools.filesystem` function. That jail is the trust boundary here
(the server, not any future client), so it belongs inside these functions,
not upstream of them.
"""

from typing import TypedDict

from app.config import settings
from app.paths import resolve_path, to_relative
from tools.filesystem import delete as delete_tool
from tools.filesystem import make_directory
from tools.filesystem import read as read_tool
from tools.filesystem import rename as rename_tool
from tools.filesystem import walk
from tools.filesystem import write as write_tool


class ReadOut(TypedDict):
    path: str
    content: str
    size_bytes: int


def read(path: str) -> ReadOut:
    """Read a UTF-8 text file's contents given a path relative to the storage root."""
    target = resolve_path(path)
    content = read_tool(str(target))
    return ReadOut(path=to_relative(target), content=content, size_bytes=len(content.encode("utf-8")))


class WriteOut(TypedDict):
    path: str
    size_bytes: int


def write(path: str, content: str) -> WriteOut:
    """Write `content` to a file at a path relative to the storage root."""
    target = resolve_path(path)
    write_tool(str(target), content)
    return WriteOut(path=to_relative(target), size_bytes=len(content.encode("utf-8")))


class DeleteOut(TypedDict):
    path: str
    deleted: bool


def delete(path: str) -> DeleteOut:
    """Delete the file or directory at a path relative to the storage root."""
    target = resolve_path(path)
    relative = to_relative(target)
    delete_tool(str(target))
    return DeleteOut(path=relative, deleted=True)


class MkdirOut(TypedDict):
    path: str
    created: bool


def mkdir(path: str) -> MkdirOut:
    """Create a directory, including missing parents, at a path relative to the storage root."""
    target = resolve_path(path)
    make_directory(str(target))
    return MkdirOut(path=to_relative(target), created=True)


class RenameOut(TypedDict):
    path: str
    new_path: str


def rename(path: str, new_path: str) -> RenameOut:
    """Move/rename a file or directory; both paths are relative to the storage root."""
    src = resolve_path(path)
    dst = resolve_path(new_path)
    original = to_relative(src)
    rename_tool(str(src), str(dst))
    return RenameOut(path=original, new_path=to_relative(dst))


class TreeEntryOut(TypedDict):
    path: str
    name: str
    is_dir: bool
    depth: int
    size: int


class ListOut(TypedDict):
    entries: list[TreeEntryOut]


def list_all() -> ListOut:
    """Flattened, depth-first listing of everything under the storage root."""
    entries = walk(settings.storage_root)
    return ListOut(
        entries=[
            TreeEntryOut(path=e.path, name=e.name, is_dir=e.is_dir, depth=e.depth, size=e.size)
            for e in entries
        ]
    )
