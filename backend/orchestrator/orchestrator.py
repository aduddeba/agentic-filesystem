"""Orchestrator -- receives a task, calls the Planner, dispatches steps to Agents.

Memory (`mcp_architecture.md` M5) doesn't exist yet, so this doesn't consult
or record to it -- that's added in M5 without changing this class's shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agents.base import Agent, StepResult
from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.catalog import ToolCatalog
from planner.plan import Plan, PlanningError, PlanStep, VerificationOutcome
from planner.planner import Planner

TaskStatus = Literal["completed", "partial", "failed"]


@dataclass
class TaskOutcome:
    task: str
    status: TaskStatus
    plan: Plan | None
    step_results: list[StepResult]
    verification: VerificationOutcome | None
    message: str


class Orchestrator:
    def __init__(
        self,
        client: MCPClientPool,
        tool_catalog: ToolCatalog,
        planner: Planner,
        agents: list[Agent],
        max_steps: int = 8,
        max_replans: int = 2,
    ) -> None:
        self._client = client
        self._tool_catalog = tool_catalog
        self._planner = planner
        self._agents = agents
        self._max_steps = max_steps
        self._max_replans = max_replans

    async def run_task(self, task: str) -> TaskOutcome:
        try:
            plan = await self._planner.plan(task, self._tool_catalog)
        except PlanningError as exc:
            return TaskOutcome(
                task=task, status="failed", plan=None, step_results=[], verification=None, message=str(exc)
            )

        results = await self._execute_steps(plan.steps[: self._max_steps])

        replans_used = 0
        while any(r.is_error for r in results) and replans_used < self._max_replans:
            try:
                plan = await self._planner.replan(task, self._tool_catalog, plan, results)
            except PlanningError:
                break
            results = await self._execute_steps(plan.steps[: self._max_steps])
            replans_used += 1

        try:
            verification = await self._planner.verify(task, results)
        except PlanningError:
            verification = None

        any_success = any(not r.is_error for r in results)
        if verification is not None and verification.satisfied:
            status: TaskStatus = "completed"
        elif any_success:
            status = "partial"
        else:
            status = "failed"

        message = verification.notes if verification is not None else "verification unavailable"
        return TaskOutcome(
            task=task, status=status, plan=plan, step_results=results, verification=verification, message=message
        )

    async def _execute_steps(self, steps: list[PlanStep]) -> list[StepResult]:
        results: list[StepResult] = []
        for step in steps:
            agent = self._find_agent(step.tool)
            if agent is None:
                results.append(
                    StepResult(
                        step=step,
                        tool_result=None,
                        is_error=True,
                        error_message=f"no agent available for tool {step.tool!r}",
                    )
                )
                continue
            results.append(await agent.handle(step, self._client))
        return results

    def _find_agent(self, tool_name: str) -> Agent | None:
        return next((agent for agent in self._agents if agent.can_handle(tool_name)), None)
