"""EditingAgent tests -- same mocked-client pattern as test_search_agent.py."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.editing_agent import EditingAgent
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


def test_can_handle_covers_filesystem_document_and_itemized_llm_tools():
    agent = EditingAgent()
    assert agent.can_handle("filesystem.read")
    assert agent.can_handle("document.extract_text")
    assert agent.can_handle("llm.chat")
    assert agent.can_handle("llm.classify")


def test_cannot_handle_tools_outside_allow_list():
    agent = EditingAgent()
    assert not agent.can_handle("embedding.generate")
    assert not agent.can_handle("llm.summarize")


@pytest.mark.anyio
async def test_handle_calls_client_and_wraps_success():
    agent = EditingAgent()
    client = _FakeClient(result=_FakeToolResult(content={"path": "a.txt", "content": "hello"}))
    step = PlanStep(tool="document.extract_text", arguments={"path": "a.txt"})

    result = await agent.handle(step, client)

    assert result.is_error is False
    assert result.tool_result == {"path": "a.txt", "content": "hello"}
    assert client.calls == [("document.extract_text", {"path": "a.txt"})]


@pytest.mark.anyio
async def test_handle_rejects_disallowed_tool_without_calling_client():
    agent = EditingAgent()
    client = _FakeClient()
    step = PlanStep(tool="semantic.search", arguments={"query": "x"})

    result = await agent.handle(step, client)

    assert result.is_error is True
    assert client.calls == []
