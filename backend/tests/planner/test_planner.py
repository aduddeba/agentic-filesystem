"""Planner tests -- mock `llm.chat` responses with fixed JSON fixtures, no real LLM call
(design doc #12: "Planner tests mock llm.chat responses... no real Ollama call")."""

from dataclasses import dataclass
from typing import Any

import pytest

from agents.base import StepResult
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
