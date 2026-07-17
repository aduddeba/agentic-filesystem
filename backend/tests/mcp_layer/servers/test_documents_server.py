"""In-memory MCP protocol tests for the Document server."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app import config as config_module
from mcp_layer.servers.documents.server import mcp


@pytest.fixture
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    return tmp_path


@pytest.mark.anyio
async def test_extract_text_reads_plain_file(storage_root):
    (storage_root / "notes.txt").write_text("hello world", encoding="utf-8")

    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("document.extract_text", {"path": "notes.txt"})
        assert result.structuredContent == {"path": "notes.txt", "content": "hello world"}


@pytest.mark.anyio
async def test_chunk_splits_text_with_overlap(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool(
            "document.chunk", {"text": "one two three four five", "chunk_size": 2, "overlap": 0}
        )
        assert result.structuredContent == {
            "chunks": [
                {"index": 0, "text": "one two"},
                {"index": 1, "text": "three four"},
                {"index": 2, "text": "five"},
            ]
        }


@pytest.mark.anyio
async def test_metadata_reports_mime_type_and_counts(storage_root):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("document.metadata", {"path": "notes.txt", "text": "hello world"})
        assert result.structuredContent == {"mime_type": "text/plain", "word_count": 2, "char_count": 11}
