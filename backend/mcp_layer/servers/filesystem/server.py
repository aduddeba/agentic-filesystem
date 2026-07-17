"""Filesystem MCP server -- read/write/delete/mkdir/rename/list, jailed to the storage root."""

from mcp.server.fastmcp import FastMCP

from .. import _runtime
from . import impl

mcp = FastMCP("filesystem", port=8801)


@mcp.tool(name="filesystem.read")
def read(path: str) -> impl.ReadOut:
    """Read a UTF-8 text file's contents given a path relative to the storage root."""
    return impl.read(path)


@mcp.tool(name="filesystem.write")
def write(path: str, content: str) -> impl.WriteOut:
    """Write `content` to a file at a path relative to the storage root."""
    return impl.write(path, content)


@mcp.tool(name="filesystem.delete")
def delete(path: str) -> impl.DeleteOut:
    """Delete the file or directory at a path relative to the storage root."""
    return impl.delete(path)


@mcp.tool(name="filesystem.mkdir")
def mkdir(path: str) -> impl.MkdirOut:
    """Create a directory, including missing parents, at a path relative to the storage root."""
    return impl.mkdir(path)


@mcp.tool(name="filesystem.rename")
def rename(path: str, new_path: str) -> impl.RenameOut:
    """Move/rename a file or directory; both paths are relative to the storage root."""
    return impl.rename(path, new_path)


@mcp.tool(name="filesystem.list")
def list_all() -> impl.ListOut:
    """Flattened, depth-first listing of everything under the storage root."""
    return impl.list_all()


app = _runtime.build_app(mcp)

if __name__ == "__main__":
    _runtime.run_main(mcp)
