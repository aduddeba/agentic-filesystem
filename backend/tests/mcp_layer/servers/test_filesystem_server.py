"""In-memory MCP protocol tests for the Filesystem server.

Uses `create_connected_server_and_client_session` -- a real `ClientSession`
talking to the real `FastMCP` server over in-memory streams, so these prove
the tools round-trip through the actual MCP protocol, not just that the
underlying Python function works.
"""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app import config as config_module
from mcp_layer.servers.filesystem.server import mcp


@pytest.fixture
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    return tmp_path


@pytest.mark.anyio
async def test_write_then_read_round_trip(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        write_result = await session.call_tool("filesystem.write", {"path": "a.txt", "content": "hi"})
        assert not write_result.isError
        assert write_result.structuredContent == {"path": "a.txt", "size_bytes": 2}

        read_result = await session.call_tool("filesystem.read", {"path": "a.txt"})
        assert read_result.structuredContent == {"path": "a.txt", "content": "hi", "size_bytes": 2}


@pytest.mark.anyio
async def test_list_reflects_written_files(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        await session.call_tool("filesystem.write", {"path": "a.txt", "content": "hi"})
        result = await session.call_tool("filesystem.list", {})
        assert [e["path"] for e in result.structuredContent["entries"]] == ["a.txt"]


@pytest.mark.anyio
async def test_mkdir_then_rename_then_delete(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        mkdir_result = await session.call_tool("filesystem.mkdir", {"path": "sub"})
        assert mkdir_result.structuredContent == {"path": "sub", "created": True}

        await session.call_tool("filesystem.write", {"path": "a.txt", "content": "hi"})
        rename_result = await session.call_tool("filesystem.rename", {"path": "a.txt", "new_path": "b.txt"})
        assert rename_result.structuredContent == {"path": "a.txt", "new_path": "b.txt"}

        delete_result = await session.call_tool("filesystem.delete", {"path": "b.txt"})
        assert delete_result.structuredContent == {"path": "b.txt", "deleted": True}


@pytest.mark.anyio
async def test_read_rejects_path_escape(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("filesystem.read", {"path": "../escape.txt"})
        assert result.isError


@pytest.mark.anyio
async def test_read_missing_file_is_an_error(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("filesystem.read", {"path": "nope.txt"})
        assert result.isError
