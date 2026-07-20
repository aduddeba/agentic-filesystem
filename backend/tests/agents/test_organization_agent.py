"""OrganizationAgent tests -- same mocked-client pattern as test_search_agent.py."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.organization_agent import OrganizationAgent
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


def test_can_handle_covers_filesystem_and_itemized_llm_tools():
    agent = OrganizationAgent()
    assert agent.can_handle("filesystem.write")
    assert agent.can_handle("filesystem.rename")
    assert agent.can_handle("llm.chat")
    assert agent.can_handle("llm.classify")


def test_cannot_handle_tools_outside_allow_list():
    agent = OrganizationAgent()
    assert not agent.can_handle("search.keyword")
    assert not agent.can_handle("llm.summarize")


@pytest.mark.anyio
async def test_handle_calls_client_and_wraps_success():
    agent = OrganizationAgent()
    client = _FakeClient(result=_FakeToolResult(content={"path": "a.txt", "size_bytes": 3}))
    step = PlanStep(tool="filesystem.write", arguments={"path": "a.txt", "content": "hi"})

    result = await agent.handle(step, client)

    assert result.is_error is False
    assert result.tool_result == {"path": "a.txt", "size_bytes": 3}
    assert client.calls == [("filesystem.write", {"path": "a.txt", "content": "hi"})]


@pytest.mark.anyio
async def test_handle_wraps_tool_error():
    agent = OrganizationAgent()
    client = _FakeClient(error=ToolError(server="filesystem", tool="filesystem.write", message="disk full"))
    step = PlanStep(tool="filesystem.write", arguments={"path": "a.txt", "content": "hi"})

    result = await agent.handle(step, client)

    assert result.is_error is True
    assert "disk full" in result.error_message
