"""Planner -- turns a task into a Plan, and later judges/revises it.

The Planner never calls `mcp_layer.servers.*` directly and never imports
`tools/*` (`mcp_architecture.md` #4). Its only two dependencies are
`ToolCatalog` (read-only tool metadata) and `llm.chat` (itself an MCP tool
call routed through the same client pool everyone else uses) -- the Planner
is just another MCP client.
"""

from __future__ import annotations

import json
from typing import Any

from agents.base import StepResult
from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.catalog import ToolCatalog

from .plan import Plan, PlanningError, PlanStep, VerificationOutcome
from .prompts import build_planning_prompt, build_replan_prompt, build_verification_prompt


class Planner:
    def __init__(self, client: MCPClientPool, chat_model: str | None = None) -> None:
        self._client = client
        self._model = chat_model

    def plan_fixed(self, tool: str, arguments: dict[str, Any] | None = None) -> Plan:
        """Build a single-step Plan directly, with no LLM call at all.

        This is the M3 "Planner v0" path (`mcp_architecture.md` #11): it proves
        the Plan -> execute -> result pipeline independent of model behavior,
        and doubles as a real, reliable way to run one known tool call through
        the Orchestrator/Agent machinery (allow-list enforcement, verification)
        without paying for or depending on an LLM call.
        """
        return Plan(goal=f"Run {tool} directly", steps=[PlanStep(tool=tool, arguments=arguments or {})])

    async def plan(self, task: str, tool_catalog: ToolCatalog) -> Plan:
        messages = build_planning_prompt(task, tool_catalog.as_planner_context())
        return await self._draft(messages)

    async def replan(self, task: str, tool_catalog: ToolCatalog, plan: Plan, results: list[StepResult]) -> Plan:
        messages = build_replan_prompt(task, tool_catalog.as_planner_context(), plan, results)
        return await self._draft(messages)

    async def verify(self, task: str, results: list[StepResult]) -> VerificationOutcome:
        messages = build_verification_prompt(task, results)
        try:
            result = await self._client.call_tool(
                "llm.chat",
                {"messages": messages, "model": self._model or "", "format": VerificationOutcome.model_json_schema()},
            )
        except Exception as exc:  # noqa: BLE001 - any transport/tool failure becomes a PlanningError
            raise PlanningError(f"verification LLM call failed: {exc}") from exc

        content = result.content["message"]["content"]
        try:
            return VerificationOutcome.model_validate_json(content)
        except (ValueError, KeyError) as exc:
            raise PlanningError(f"could not parse verification response: {exc}") from exc

    async def _draft(self, messages: list[dict[str, str]]) -> Plan:
        try:
            result = await self._client.call_tool(
                "llm.chat",
                {"messages": messages, "model": self._model or "", "format": Plan.model_json_schema()},
            )
        except Exception as exc:  # noqa: BLE001 - any transport/tool failure becomes a PlanningError
            raise PlanningError(f"planning LLM call failed: {exc}") from exc

        try:
            content = result.content["message"]["content"]
            return Plan.model_validate_json(content)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise PlanningError(f"could not parse plan response: {exc}") from exc
