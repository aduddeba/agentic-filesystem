"""Agent Protocol + BaseAgent -- shared allow-list enforcement.

Every agent is intentionally dumb (`mcp_architecture.md` #10.2): it checks a
step's tool falls within its namespace/tool allow-list, forwards the call to
`MCPClientPool`, and wraps the outcome as a `StepResult`. All judgment (what
to call, in what order, whether the goal was met) lives in the Planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from mcp_layer.client.errors import ToolError
from mcp_layer.client.pool import MCPClientPool
from planner.plan import PlanStep


@dataclass
class StepResult:
    step: PlanStep
    tool_result: dict[str, Any] | None
    is_error: bool
    error_message: str | None = None


class Agent(Protocol):
    name: str
    allowed_namespaces: frozenset[str]

    async def handle(self, step: PlanStep, client: MCPClientPool) -> StepResult: ...
    def can_handle(self, tool_name: str) -> bool: ...


class BaseAgent:
    name: str = "base"
    allowed_namespaces: frozenset[str] = frozenset()
    allowed_tools: frozenset[str] = frozenset()

    def can_handle(self, tool_name: str) -> bool:
        namespace = tool_name.split(".", 1)[0]
        return namespace in self.allowed_namespaces or tool_name in self.allowed_tools

    async def handle(self, step: PlanStep, client: MCPClientPool) -> StepResult:
        if not self.can_handle(step.tool):
            return StepResult(
                step=step,
                tool_result=None,
                is_error=True,
                error_message=f"{self.name} agent isn't allowed to call {step.tool!r}",
            )
        try:
            result = await client.call_tool(step.tool, step.arguments)
        except ToolError as exc:
            return StepResult(step=step, tool_result=None, is_error=True, error_message=str(exc))
        return StepResult(step=step, tool_result=result.content, is_error=False)
