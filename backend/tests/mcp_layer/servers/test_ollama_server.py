"""In-memory MCP protocol tests for the Ollama server, against a real local
Ollama daemon -- skipped if one isn't reachable, mirroring the
skip-if-Postgres-unreachable pattern in `tests/conftest.py`."""

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app.config import settings
from mcp_layer.servers.ollama.server import mcp


def _ollama_reachable() -> bool:
    try:
        httpx.get(f"{settings.ollama_host}/api/tags", timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _ollama_reachable(), reason=f"Ollama not reachable at {settings.ollama_host}")


@pytest.mark.anyio
async def test_chat_returns_assistant_message():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool(
            "llm.chat", {"messages": [{"role": "user", "content": "Reply with exactly the word: pong"}]}
        )
        assert not result.isError
        message = result.structuredContent["message"]
        assert message["role"] == "assistant"
        assert message["content"]


@pytest.mark.anyio
async def test_generate_returns_response_text():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("llm.generate", {"prompt": "Say hello."})
        assert not result.isError
        assert result.structuredContent["response"]


@pytest.mark.anyio
async def test_embed_returns_fixed_dimension_vector():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("llm.embed", {"text": "hello world"})
        assert not result.isError
        assert len(result.structuredContent["embedding"]) == 384


@pytest.mark.anyio
async def test_summarize_returns_shorter_text():
    long_text = "The quick brown fox jumps over the lazy dog. " * 20
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("llm.summarize", {"text": long_text, "max_words": 15})
        assert not result.isError
        summary = result.structuredContent["summary"]
        assert summary
        assert len(summary.split()) < len(long_text.split())


@pytest.mark.anyio
async def test_classify_returns_one_of_the_given_labels():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool(
            "llm.classify", {"text": "I absolutely loved this movie!", "labels": ["positive", "negative"]}
        )
        assert not result.isError
        content = result.structuredContent
        assert content["label"] in ("positive", "negative")
        assert 0.0 <= content["confidence"] <= 1.0


@pytest.mark.anyio
async def test_classify_rejects_single_label():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("llm.classify", {"text": "hello", "labels": ["only-one"]})
        assert result.isError
