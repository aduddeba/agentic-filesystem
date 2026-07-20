"""Orchestrator -- receives a task, calls the Planner, dispatches steps to Agents,
consults Memory before planning and records to it after every run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agents.base import Agent, StepResult
from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.catalog import ToolCatalog
from memory.schemas import MemoryContext
from memory.store import MUTATING_FILESYSTEM_TOOLS, MemoryStore
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
        memory: MemoryStore | None = None,
    ) -> None:
        self._client = client
        self._tool_catalog = tool_catalog
        self._planner = planner
        self._agents = agents
        self._max_steps = max_steps
        self._max_replans = max_replans
        self._memory = memory

    async def run_task(
        self, task: str, *, fixed_tool: str | None = None, fixed_arguments: dict[str, Any] | None = None
    ) -> TaskOutcome:
        if fixed_tool is not None:
            outcome = await self._run_fixed_plan(task, fixed_tool, fixed_arguments)
            self._record_to_memory(outcome)
            return outcome

        memory_context = self._load_memory_context()
        try:
            plan = await self._planner.plan(task, self._tool_catalog, memory_context)
        except PlanningError as exc:
            outcome = TaskOutcome(
                task=task, status="failed", plan=None, step_results=[], verification=None, message=str(exc)
            )
            self._record_to_memory(outcome)
            return outcome

        results = await self._execute_steps(plan.steps[: self._max_steps])

        replans_used = 0
        while not self._any_succeeded(results) and replans_used < self._max_replans:
            try:
                plan = await self._planner.replan(task, self._tool_catalog, plan, results)
            except PlanningError:
                break
            results = await self._execute_steps(plan.steps[: self._max_steps])
            replans_used += 1

        if not self._any_succeeded(results):
            # Nothing actually ran (an empty plan -- e.g. the model decided no tool was
            # needed when one was required -- or every step errored). Report this as a
            # failure directly rather than asking the LLM to "verify" a run with no
            # results: it has nothing real to judge and will otherwise happily hallucinate
            # a "satisfied: true" answer to the task from its own knowledge, which looks
            # like a successful run but did none of the requested work.
            message = "The plan had no steps to execute" if not results else "No step completed successfully"
            outcome = TaskOutcome(
                task=task, status="failed", plan=plan, step_results=results, verification=None, message=message
            )
            self._record_to_memory(outcome)
            return outcome

        try:
            verification = await self._planner.verify(task, results)
        except PlanningError:
            verification = None

        status: TaskStatus = "completed" if verification is not None and verification.satisfied else "partial"
        message = verification.notes if verification is not None else "verification unavailable"
        outcome = TaskOutcome(
            task=task, status=status, plan=plan, step_results=results, verification=verification, message=message
        )
        self._record_to_memory(outcome)
        return outcome

    def _load_memory_context(self) -> MemoryContext | None:
        if self._memory is None:
            return None
        recent = self._memory.recent_tasks()
        return MemoryContext(
            recent_tasks=[f"{record.task} -> {record.summary}" for record in recent],
            preferences=self._memory.preferences(),
        )

    def _record_to_memory(self, outcome: TaskOutcome) -> None:
        if self._memory is None:
            return
        file_deltas = [
            path
            for result in outcome.step_results
            if not result.is_error and result.step.tool in MUTATING_FILESYSTEM_TOOLS
            for path in (result.step.arguments.get("path"), result.step.arguments.get("new_path"))
            if path
        ]
        self._memory.record_task(outcome.task, outcome.message, file_deltas, status=outcome.status)

    @staticmethod
    def _any_succeeded(results: list[StepResult]) -> bool:
        return any(not r.is_error for r in results)

    async def _run_fixed_plan(self, task: str, tool: str, arguments: dict[str, Any] | None) -> TaskOutcome:
        """The M3 "Planner v0" path: a single-step Plan built directly (no LLM call anywhere
        in this path -- no planning, no replanning, no verification), proving Plan -> execute
        -> result end to end. Useful on its own too, as a reliable way to run one known tool
        call through the same allow-list-enforced Orchestrator/Agent machinery."""
        plan = self._planner.plan_fixed(tool, arguments)
        results = await self._execute_steps(plan.steps)
        result = results[0]
        status: TaskStatus = "failed" if result.is_error else "completed"
        message = result.error_message if result.is_error else "ok"
        return TaskOutcome(
            task=task, status=status, plan=plan, step_results=results, verification=None, message=message or "ok"
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
