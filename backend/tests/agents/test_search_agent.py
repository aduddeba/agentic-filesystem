"""SearchAgent tests -- mock MCPClientPool entirely, assert only the namespace
allow-list logic and result-wrapping (design doc #12: agents have no other logic)."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.search_agent import SearchAgent
from mcp_layer.client.errors import ToolError
from planner.plan import PlanStep


@dataclass
class _FakeToolResult:
    content: dict[str, Any]


class _FakeClient:
    def __init__(self, result: _FakeToolResult | None = None, error: ToolError | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, arguments: dict) -> _FakeToolResult:
        self.calls.append((tool_name, arguments))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def test_can_handle_covers_allowed_namespaces_and_extra_tool():
    agent = SearchAgent()
    assert agent.can_handle("search.keyword")
    assert agent.can_handle("semantic.search")
    assert agent.can_handle("llm.classify")


def test_cannot_handle_tools_outside_allow_list():
    agent = SearchAgent()
    assert not agent.can_handle("filesystem.write")
    assert not agent.can_handle("llm.chat")


@pytest.mark.anyio
async def test_handle_calls_client_and_wraps_success():
    agent = SearchAgent()
    client = _FakeClient(result=_FakeToolResult(content={"matches": []}))
    step = PlanStep(tool="search.keyword", arguments={"query": "TODO"})

    result = await agent.handle(step, client)

    assert result.is_error is False
    assert result.tool_result == {"matches": []}
    assert client.calls == [("search.keyword", {"query": "TODO"})]


@pytest.mark.anyio
async def test_handle_rejects_disallowed_tool_without_calling_client():
    agent = SearchAgent()
    client = _FakeClient()
    step = PlanStep(tool="filesystem.write", arguments={"path": "x", "content": "y"})

    result = await agent.handle(step, client)

    assert result.is_error is True
    assert "not allowed" in result.error_message.lower() or "isn't allowed" in result.error_message.lower()
    assert client.calls == []


@pytest.mark.anyio
async def test_handle_wraps_tool_error():
    agent = SearchAgent()
    client = _FakeClient(error=ToolError(server="search", tool="search.keyword", message="boom"))
    step = PlanStep(tool="search.keyword", arguments={"query": "TODO"})

    result = await agent.handle(step, client)

    assert result.is_error is True
    assert "boom" in result.error_message
