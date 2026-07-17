"""In-memory MCP protocol tests for the Embedding server."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_layer.servers.embeddings.server import mcp
from tools.embeddings import EMBEDDING_DIM


@pytest.mark.anyio
async def test_query_returns_a_vector_of_expected_dimension():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("embedding.query", {"text": "what is the capital of France?"})
        assert not result.isError
        vector = result.structuredContent["embedding"]
        assert len(vector) == EMBEDDING_DIM


@pytest.mark.anyio
async def test_generate_returns_one_vector_per_text():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("embedding.generate", {"texts": ["hello world", "goodbye world"]})
        vectors = result.structuredContent["embeddings"]
        assert len(vectors) == 2
        assert all(len(v) == EMBEDDING_DIM for v in vectors)


@pytest.mark.anyio
async def test_generate_empty_list_returns_empty_list():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("embedding.generate", {"texts": []})
        assert result.structuredContent == {"embeddings": []}
