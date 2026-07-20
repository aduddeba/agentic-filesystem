"""Orchestrator tests -- mock Planner + a fake MCPClientPool, real Orchestrator + real
SearchAgent. This is also where the M3 goal lives: proving a `Plan` runs end-to-end
through the pipeline (Orchestrator -> Agent -> "MCPClientPool") independent of any LLM
call, by handing the Orchestrator a stub Planner that returns a pre-built Plan."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from agents.organization_agent import OrganizationAgent
from agents.search_agent import SearchAgent
from memory.schemas import MemoryContext
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
    verify_calls: int = 0
    last_memory_context: MemoryContext | None = None

    async def plan(self, task: str, tool_catalog, memory_context: MemoryContext | None = None) -> Plan:
        self.plan_calls += 1
        self.last_memory_context = memory_context
        if self.plan_error is not None:
            raise self.plan_error
        return self.plans[0]

    async def replan(self, task: str, tool_catalog, plan: Plan, results) -> Plan:
        self.replan_calls += 1
        return self.plans[min(self.replan_calls, len(self.plans) - 1)]

    async def verify(self, task: str, results) -> VerificationOutcome:
        self.verify_calls += 1
        assert self.verification is not None
        return self.verification

    def plan_fixed(self, tool: str, arguments: dict | None = None) -> Plan:
        return Plan(goal=f"Run {tool} directly", steps=[PlanStep(tool=tool, arguments=arguments or {})])


@dataclass
class _FakeTaskRecord:
    task: str
    summary: str


@dataclass
class _FakeMemory:
    """Stands in for MemoryStore -- records what was written, returns canned reads."""

    canned_recent_tasks: list[_FakeTaskRecord] = field(default_factory=list)
    canned_preferences: dict[str, str] = field(default_factory=dict)
    recorded: list[dict] = field(default_factory=list)

    def recent_tasks(self, limit: int = 10) -> list[_FakeTaskRecord]:
        return self.canned_recent_tasks[:limit]

    def preferences(self) -> dict[str, str]:
        return self.canned_preferences

    def record_task(self, task: str, summary: str, file_deltas: list[str], status: str = "unknown") -> None:
        self.recorded.append({"task": task, "summary": summary, "file_deltas": file_deltas, "status": status})


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
async def test_run_task_with_zero_step_plan_is_reported_as_failed_not_completed():
    """Regression: a plan with 0 steps (the model decided no tool was needed, even
    though the task required one) must never come back "completed" just because the
    verification LLM call hallucinated satisfied=True with nothing real to judge."""
    empty_plan = Plan(goal="find TODOs", steps=[])
    planner = _FakePlanner(
        plans=[empty_plan], verification=VerificationOutcome(satisfied=True, notes="hallucinated success")
    )
    orchestrator = Orchestrator(client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task("find TODOs")

    assert outcome.status == "failed"
    assert outcome.step_results == []
    assert outcome.verification is None
    assert planner.verify_calls == 0
    assert "no steps" in outcome.message.lower()


@pytest.mark.anyio
async def test_run_task_replans_when_plan_has_zero_steps():
    empty_plan = Plan(goal="find TODOs", steps=[])
    working_plan = Plan(goal="find TODOs", steps=[PlanStep(tool="search.keyword", arguments={"query": "TODO"})])
    client = _FakeClient(responses={"search.keyword": {"matches": [{"path": "a.txt"}]}})
    planner = _FakePlanner(
        plans=[empty_plan, working_plan], verification=VerificationOutcome(satisfied=True, notes="found it")
    )
    orchestrator = Orchestrator(client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task("find TODOs")

    assert planner.replan_calls == 1
    assert outcome.status == "completed"
    assert client.calls == ["search.keyword"]


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


@pytest.mark.anyio
async def test_run_task_with_no_memory_configured_does_not_touch_it():
    """Every test above constructs Orchestrator without `memory=` -- this is the explicit
    version of that, confirming the default is a true no-op, not just untested."""
    plan = Plan(goal="find TODOs", steps=[PlanStep(tool="search.keyword", arguments={"query": "TODO"})])
    client = _FakeClient(responses={"search.keyword": {"matches": []}})
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=True, notes="ok"))
    orchestrator = Orchestrator(client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()])

    outcome = await orchestrator.run_task("find TODOs")

    assert outcome.status == "completed"
    assert planner.last_memory_context is None


@pytest.mark.anyio
async def test_run_task_loads_memory_context_before_planning():
    plan = Plan(goal="find TODOs", steps=[])
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=True, notes="ok"))
    memory = _FakeMemory(
        canned_recent_tasks=[_FakeTaskRecord(task="search FastAPI", summary="found 3 files")],
        canned_preferences={"sort_order": "newest first"},
    )
    orchestrator = Orchestrator(
        client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()], memory=memory
    )

    await orchestrator.run_task("find TODOs")

    assert planner.last_memory_context == MemoryContext(
        recent_tasks=["search FastAPI -> found 3 files"], preferences={"sort_order": "newest first"}
    )


@pytest.mark.anyio
async def test_run_task_records_to_memory_exactly_once_with_file_deltas():
    plan = Plan(
        goal="write a file",
        steps=[PlanStep(tool="filesystem.write", arguments={"path": "notes.txt", "content": "hi"})],
    )
    client = _FakeClient(responses={"filesystem.write": {"path": "notes.txt", "size_bytes": 2}})
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=True, notes="wrote it"))
    memory = _FakeMemory()
    orchestrator = Orchestrator(
        client=client, tool_catalog=object(), planner=planner, agents=[OrganizationAgent()], memory=memory
    )

    outcome = await orchestrator.run_task("write a file")

    assert len(memory.recorded) == 1
    assert memory.recorded[0] == {
        "task": "write a file",
        "summary": outcome.message,
        "file_deltas": ["notes.txt"],
        "status": "completed",
    }


@pytest.mark.anyio
async def test_run_task_records_to_memory_on_planning_error():
    planner = _FakePlanner(plan_error=PlanningError("model returned garbage"))
    memory = _FakeMemory()
    orchestrator = Orchestrator(
        client=_FakeClient(), tool_catalog=object(), planner=planner, agents=[SearchAgent()], memory=memory
    )

    await orchestrator.run_task("find TODOs")

    assert len(memory.recorded) == 1
    assert memory.recorded[0]["status"] == "failed"
    assert memory.recorded[0]["file_deltas"] == []


@pytest.mark.anyio
async def test_run_task_records_to_memory_on_fixed_tool_path():
    client = _FakeClient(responses={"search.keyword": {"matches": []}})
    planner = _FakePlanner()
    memory = _FakeMemory()
    orchestrator = Orchestrator(
        client=client, tool_catalog=object(), planner=planner, agents=[SearchAgent()], memory=memory
    )

    await orchestrator.run_task("run search directly", fixed_tool="search.keyword", fixed_arguments={"query": "x"})

    assert len(memory.recorded) == 1
    assert memory.recorded[0]["status"] == "completed"


@pytest.mark.anyio
async def test_run_task_does_not_record_a_failed_steps_path_as_a_file_delta():
    plan = Plan(
        goal="mixed",
        steps=[
            PlanStep(tool="search.keyword", arguments={"query": "TODO"}),
            PlanStep(tool="filesystem.write", arguments={"path": "should-not-appear.txt"}),
        ],
    )
    client = _FakeClient(responses={"search.keyword": {"matches": []}})
    planner = _FakePlanner(plans=[plan], verification=VerificationOutcome(satisfied=False, notes="partial"))
    memory = _FakeMemory()
    orchestrator = Orchestrator(
        client=client,
        tool_catalog=object(),
        planner=planner,
        agents=[SearchAgent()],  # can't handle filesystem.write -> that step errors
        memory=memory,
        max_replans=0,
    )

    await orchestrator.run_task("mixed")

    assert memory.recorded[0]["file_deltas"] == []
