"""In-memory MCP protocol tests for the Vector server.

Needs a real Postgres+pgvector -- reuses the same self-provisioning
`pg_engine` fixture (backend/tests/conftest.py) the plain indexing/search
tests use, and skips gracefully if Postgres isn't reachable.

`impl.py` does `from app.database import SessionLocal`, binding its own
module-level name -- so the session factory used by a running tool call has
to be patched on `vectors_impl` itself, not on `app.database` (same
"from X import Y" rebind pattern `tests/conftest.py`'s `pg_client` fixture
uses for `main_module.SessionLocal`).
"""

import mcp_layer.servers.vectors.impl as vectors_impl
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from sqlalchemy.orm import sessionmaker

from app.models import FileRecord
from mcp_layer.servers.vectors.server import mcp


@pytest.fixture
def vectors_session_factory(pg_engine, monkeypatch):
    testing_session_local = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(vectors_impl, "SessionLocal", testing_session_local)
    return testing_session_local


def _make_indexed_record(session_factory, path: str) -> None:
    session = session_factory()
    session.add(FileRecord(path=path, name=path.split("/")[-1], is_dir=False, size=0))
    session.commit()
    session.close()


@pytest.mark.anyio
async def test_insert_then_search_round_trip(vectors_session_factory):
    _make_indexed_record(vectors_session_factory, "note.txt")

    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        insert_result = await session.call_tool(
            "semantic.insert", {"file_path": "note.txt", "chunk_index": 0, "text": "the quick brown fox"}
        )
        assert not insert_result.isError
        assert "chunk_id" in insert_result.structuredContent

        search_result = await session.call_tool("semantic.search", {"query": "a fast fox", "mode": "vector"})
        matches = search_result.structuredContent["matches"]
        assert matches[0]["path"] == "note.txt"


@pytest.mark.anyio
async def test_delete_removes_chunks(vectors_session_factory):
    _make_indexed_record(vectors_session_factory, "note.txt")

    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        await session.call_tool(
            "semantic.insert", {"file_path": "note.txt", "chunk_index": 0, "text": "the quick brown fox"}
        )
        delete_result = await session.call_tool("semantic.delete", {"file_path": "note.txt"})
        assert delete_result.structuredContent == {"file_path": "note.txt", "deleted": 1}

        search_result = await session.call_tool("semantic.search", {"query": "fox", "mode": "vector"})
        assert search_result.structuredContent["matches"] == []


@pytest.mark.anyio
async def test_insert_unknown_file_is_an_error(vectors_session_factory):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool(
            "semantic.insert", {"file_path": "nope.txt", "chunk_index": 0, "text": "text"}
        )
        assert result.isError


@pytest.mark.anyio
async def test_blank_query_returns_no_matches(vectors_session_factory):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("semantic.search", {"query": "  "})
        assert result.structuredContent == {"matches": []}
