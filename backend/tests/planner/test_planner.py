"""Planner tests -- mock `llm.chat` responses with fixed JSON fixtures, no real LLM call
(design doc #12: "Planner tests mock llm.chat responses... no real Ollama call")."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.base import StepResult
from memory.schemas import MemoryContext
from planner.plan import Plan, PlanningError, PlanStep
from planner.planner import Planner


@dataclass
class _FakeResult:
    content: dict[str, Any]


class _FakeClient:
    """Stands in for MCPClientPool: records calls, returns a queued chat response."""

    def __init__(self, chat_content: str | None = None, raise_error: Exception | None = None) -> None:
        self.chat_content = chat_content
        self.raise_error = raise_error
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, arguments: dict) -> _FakeResult:
        self.calls.append((tool_name, arguments))
        if self.raise_error is not None:
            raise self.raise_error
        return _FakeResult(content={"message": {"role": "assistant", "content": self.chat_content}})


class _FakeCatalog:
    def as_planner_context(self) -> str:
        return "search.keyword: keyword search\n  input: {}"


def test_plan_fixed_builds_single_step_plan_without_any_llm_call():
    client = _FakeClient(chat_content="should never be read")
    planner = Planner(client)

    plan = planner.plan_fixed("search.keyword", {"query": "TODO"})

    assert plan.steps == [PlanStep(tool="search.keyword", arguments={"query": "TODO"})]
    assert client.calls == []


def test_plan_fixed_defaults_arguments_to_empty_dict():
    planner = Planner(_FakeClient())

    plan = planner.plan_fixed("filesystem.list")

    assert plan.steps == [PlanStep(tool="filesystem.list", arguments={})]


@pytest.mark.anyio
async def test_plan_parses_valid_json_into_plan():
    plan_json = Plan(goal="find todos", steps=[PlanStep(tool="search.keyword", arguments={"query": "TODO"})])
    client = _FakeClient(chat_content=plan_json.model_dump_json())
    planner = Planner(client)

    plan = await planner.plan("find TODOs", _FakeCatalog())

    assert plan.goal == "find todos"
    assert plan.steps == [PlanStep(tool="search.keyword", arguments={"query": "TODO"})]
    assert client.calls[0][0] == "llm.chat"


@pytest.mark.anyio
async def test_plan_renders_memory_context_into_the_prompt_when_provided():
    plan_json = Plan(goal="find todos", steps=[])
    client = _FakeClient(chat_content=plan_json.model_dump_json())
    planner = Planner(client)
    memory_context = MemoryContext(
        recent_tasks=["search FastAPI -> found 3 files"], preferences={"sort_order": "newest first"}
    )

    await planner.plan("find TODOs", _FakeCatalog(), memory_context)

    sent_messages = str(client.calls[0][1]["messages"])
    assert "search FastAPI -> found 3 files" in sent_messages
    assert "sort_order: newest first" in sent_messages


@pytest.mark.anyio
async def test_plan_without_memory_context_omits_memory_block():
    plan_json = Plan(goal="find todos", steps=[])
    client = _FakeClient(chat_content=plan_json.model_dump_json())
    planner = Planner(client)

    await planner.plan("find TODOs", _FakeCatalog())

    sent_messages = str(client.calls[0][1]["messages"])
    assert "Recent tasks" not in sent_messages
    assert "preferences" not in sent_messages.lower()


@pytest.mark.anyio
async def test_plan_raises_planning_error_on_malformed_json():
    client = _FakeClient(chat_content="not valid json at all")
    planner = Planner(client)

    with pytest.raises(PlanningError):
        await planner.plan("find TODOs", _FakeCatalog())


@pytest.mark.anyio
async def test_plan_raises_planning_error_when_llm_chat_fails():
    client = _FakeClient(raise_error=RuntimeError("connection refused"))
    planner = Planner(client)

    with pytest.raises(PlanningError):
        await planner.plan("find TODOs", _FakeCatalog())


@pytest.mark.anyio
async def test_replan_sends_prior_plan_and_results_in_prompt():
    prior_plan = Plan(goal="find todos", steps=[PlanStep(tool="search.keyword", arguments={"query": "TODO"})])
    revised = Plan(goal="find todos", steps=[PlanStep(tool="semantic.search", arguments={"query": "TODO"})])
    results = [
        StepResult(step=prior_plan.steps[0], tool_result=None, is_error=True, error_message="no matches")
    ]
    client = _FakeClient(chat_content=revised.model_dump_json())
    planner = Planner(client)

    plan = await planner.replan("find TODOs", _FakeCatalog(), prior_plan, results)

    assert plan == revised
    sent_messages = client.calls[0][1]["messages"]
    assert "no matches" in str(sent_messages)


@pytest.mark.anyio
async def test_verify_parses_satisfied_outcome():
    step = PlanStep(tool="search.keyword", arguments={"query": "TODO"})
    results = [StepResult(step=step, tool_result={"matches": []}, is_error=False)]
    client = _FakeClient(chat_content='{"satisfied": true, "notes": "found everything"}')
    planner = Planner(client)

    outcome = await planner.verify("find TODOs", results)

    assert outcome.satisfied is True
    assert outcome.notes == "found everything"


@pytest.mark.anyio
async def test_verify_raises_planning_error_on_malformed_json():
    step = PlanStep(tool="search.keyword", arguments={"query": "TODO"})
    results = [StepResult(step=step, tool_result=None, is_error=True, error_message="boom")]
    client = _FakeClient(chat_content="nonsense")
    planner = Planner(client)

    with pytest.raises(PlanningError):
        await planner.verify("find TODOs", results)
