"""In-memory MCP protocol tests for the Search server."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app import config as config_module
from mcp_layer.servers.search.server import mcp


@pytest.fixture
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    return tmp_path


@pytest.mark.anyio
async def test_keyword_search_finds_match(storage_root):
    (storage_root / "notes.txt").write_text("hello world\nTODO: fix this\n", encoding="utf-8")

    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("search.keyword", {"query": "TODO"})
        assert not result.isError
        matches = result.structuredContent["matches"]
        assert len(matches) == 1
        assert matches[0]["path"] == "notes.txt"
        assert matches[0]["line"] == 2


@pytest.mark.anyio
async def test_blank_query_returns_no_matches(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("search.keyword", {"query": "   "})
        assert result.structuredContent == {"matches": []}
