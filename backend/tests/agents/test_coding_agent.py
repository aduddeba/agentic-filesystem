"""CodingAgent tests -- mocked client, so this exercises git.*/python.* allow-listing without
needing real Git/Python MCP servers (those don't exist until M6; this agent isn't registered
in app/mcp_runtime.py's live agent list yet either -- see coding_agent.py's docstring)."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.coding_agent import CodingAgent
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


def test_can_handle_covers_python_git_filesystem_and_search():
    agent = CodingAgent()
    assert agent.can_handle("python.run")
    assert agent.can_handle("git.status")
    assert agent.can_handle("filesystem.read")
    assert agent.can_handle("search.keyword")


def test_cannot_handle_tools_outside_allow_list():
    agent = CodingAgent()
    assert not agent.can_handle("llm.chat")
    assert not agent.can_handle("embedding.generate")


@pytest.mark.anyio
async def test_handle_wraps_a_tool_error_for_a_not_yet_existing_server():
    """Regression coverage for the KeyError->ToolError fix in mcp_layer/client/pool.py:
    a git.*/python.* call against a pool with no such server registered must come back
    as a graceful StepResult, not an unhandled exception."""
    agent = CodingAgent()
    client = _FakeClient(error=ToolError(server="unknown", tool="git.status", message="no MCP server registers this tool"))
    step = PlanStep(tool="git.status", arguments={})

    result = await agent.handle(step, client)

    assert result.is_error is True
    assert "no MCP server registers this tool" in result.error_message
