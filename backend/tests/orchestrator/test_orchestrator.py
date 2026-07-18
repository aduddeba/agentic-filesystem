"""Orchestrator tests -- mock Planner + a fake MCPClientPool, real Orchestrator + real
SearchAgent. This is also where the M3 goal lives: proving a `Plan` runs end-to-end
through the pipeline (Orchestrator -> Agent -> "MCPClientPool") independent of any LLM
call, by handing the Orchestrator a stub Planner that returns a pre-built Plan."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from agents.search_agent import SearchAgent
from orchestrator.orchestrator import Orchestrator
from planner.plan import Plan, PlanningError, PlanStep, VerificationOutcome


@dataclass
class _FakeToolResult:
    content: dict[str, Any]


class _FakeClient:
    """Stands in for MCPClientPool.call_tool -- returns a canned result per tool name."""

    def __init__(self, responses: dict[str, dict] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[str] = []

    async def call_tool(self, tool_name: str, arguments: dict) -> _FakeToolResult:
        self.calls.append(tool_name)
        if tool_name not in self.responses:
            raise KeyError(f"no canned response for {tool_name!r}")
        return _FakeToolResult(content=self.responses[tool_name])


@dataclass
class _FakePlanner:
    """Stands in for Planner -- returns pre-built Plan/VerificationOutcome, no LLM call."""

    plans: list[Plan] = field(default_factory=list)
    verification: VerificationOutcome | None = None
    plan_error: Exception | None = None
    plan_calls: int = 0
    replan_calls: int = 0

    async def plan(self, task: str, tool_catalog) -> Plan:
        self.plan_calls += 1
        if self.plan_error is not None:
            raise self.plan_error
        return self.plans[0]

    async def replan(self, task: str, tool_catalog, plan: Plan, results) -> Plan:
        self.replan_calls += 1
        return self.plans[min(self.replan_calls, len(self.plans) - 1)]

    async def verify(self, task: str, results) -> VerificationOutcome:
        assert self.verification is not None
        return self.verification

    def plan_fixed(self, tool: str, arguments: dict | None = None) -> Plan:
        return Plan(goal=f"Run {tool} directly", steps=[PlanStep(tool=tool, arguments=arguments or {})])


@pytest.mark.anyio
async def test_run_task_executes_plan_end_to_end_via_search_agent():
    """The M3 proof: a Plan built directly (not via an LLM) runs through the real
    Orchestrator + real SearchAgent against a stub tool result."""
    plan = Plan(goal="find TODOs", steps=[PlanStep(tool="search.keyword", arguments={"query": "TODO"})])
    client = _FakeClient(responses={"search.keyword": {"matches": [{"path": "a.txt", "line": 1, "text": "TODO"}]}})
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=True, notes="found it"))
    orchestrator = Orchestrator(client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task("find TODOs")

    assert outcome.status == "completed"
    assert len(outcome.step_results) == 1
    assert outcome.step_results[0].is_error is False
    assert outcome.step_results[0].tool_result["matches"][0]["path"] == "a.txt"
    assert client.calls == ["search.keyword"]


@pytest.mark.anyio
async def test_run_task_returns_failed_outcome_on_planning_error():
    planner = _FakePlanner(plan_error=PlanningError("model returned garbage"))
    orchestrator = Orchestrator(client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task("find TODOs")

    assert outcome.status == "failed"
    assert outcome.plan is None
    assert outcome.step_results == []


@pytest.mark.anyio
async def test_run_task_caps_steps_at_max_steps():
    steps = [PlanStep(tool="search.keyword", arguments={"query": str(i)}) for i in range(5)]
    plan = Plan(goal="many searches", steps=steps)
    client = _FakeClient(responses={"search.keyword": {"matches": []}})
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=True, notes="ok"))
    orchestrator = Orchestrator(
        client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()], max_steps=2
    )

    outcome = await orchestrator.run_task("many searches")

    assert len(outcome.step_results) == 2
    assert len(client.calls) == 2


@pytest.mark.anyio
async def test_run_task_records_graceful_error_when_no_agent_available():
    plan = Plan(goal="write a file", steps=[PlanStep(tool="filesystem.write", arguments={"path": "x"})])
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=False, notes="nothing done"))
    orchestrator = Orchestrator(client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task("write a file")

    assert outcome.status == "failed"
    assert outcome.step_results[0].is_error is True
    assert "no agent" in outcome.step_results[0].error_message


@pytest.mark.anyio
async def test_run_task_replans_on_failure_up_to_max_replans():
    failing_plan = Plan(goal="search", steps=[PlanStep(tool="filesystem.write", arguments={})])
    planner = _FakePlanner(
        plans=[failing_plan], verification=VerificationOutcome(satisfied=False, notes="still failing")
    )
    orchestrator = Orchestrator(
        client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()], max_replans=2
    )

    outcome = await orchestrator.run_task("search")

    assert planner.replan_calls == 2
    assert outcome.status == "failed"


@pytest.mark.anyio
async def test_run_task_with_fixed_tool_skips_llm_entirely_on_success():
    client = _FakeClient(responses={"search.keyword": {"matches": [{"path": "a.txt"}]}})
    planner = _FakePlanner()
    orchestrator = Orchestrator(client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task(
        "run search directly", fixed_tool="search.keyword", fixed_arguments={"query": "TODO"}
    )

    assert outcome.status == "completed"
    assert outcome.verification is None
    assert planner.plan_calls == 0
    assert planner.replan_calls == 0
    assert client.calls == ["search.keyword"]


@pytest.mark.anyio
async def test_run_task_with_fixed_tool_reports_failure_without_replanning():
    planner = _FakePlanner()
    orchestrator = Orchestrator(
        client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()], max_replans=2
    )

    outcome = await orchestrator.run_task("run filesystem.write directly", fixed_tool="filesystem.write")

    assert outcome.status == "failed"
    assert planner.replan_calls == 0
    assert "no agent" in outcome.step_results[0].error_message


@pytest.mark.anyio
async def test_run_task_uses_partial_status_when_some_steps_succeed():
    plan = Plan(
        goal="mixed",
        steps=[
            PlanStep(tool="search.keyword", arguments={"query": "TODO"}),
            PlanStep(tool="filesystem.write", arguments={}),
        ],
    )
    client = _FakeClient(responses={"search.keyword": {"matches": []}})
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=False, notes="partial"))
    orchestrator = Orchestrator(
        client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()], max_replans=0
    )

    outcome = await orchestrator.run_task("mixed")

    assert outcome.status == "partial"
