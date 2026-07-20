"""AnalysisAgent tests -- same mocked-client pattern as test_search_agent.py."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.analysis_agent import AnalysisAgent
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


def test_can_handle_covers_document_embedding_and_itemized_llm_tools():
    agent = AnalysisAgent()
    assert agent.can_handle("document.metadata")
    assert agent.can_handle("embedding.generate")
    assert agent.can_handle("llm.summarize")
    assert agent.can_handle("llm.classify")


def test_cannot_handle_tools_outside_allow_list():
    agent = AnalysisAgent()
    assert not agent.can_handle("filesystem.write")
    assert not agent.can_handle("search.keyword")


@pytest.mark.anyio
async def test_handle_calls_client_and_wraps_success():
    agent = AnalysisAgent()
    client = _FakeClient(result=_FakeToolResult(content={"summary": "a file about widgets"}))
    step = PlanStep(tool="llm.summarize", arguments={"text": "widgets widgets widgets"})

    result = await agent.handle(step, client)

    assert result.is_error is False
    assert result.tool_result == {"summary": "a file about widgets"}


@pytest.mark.anyio
async def test_handle_wraps_tool_error():
    agent = AnalysisAgent()
    client = _FakeClient(error=ToolError(server="ollama", tool="llm.summarize", message="model unavailable"))
    step = PlanStep(tool="llm.summarize", arguments={"text": "x"})

    result = await agent.handle(step, client)

    assert result.is_error is True
    assert "model unavailable" in result.error_message
