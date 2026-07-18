"""/api/tasks route tests -- stub the orchestrator so these don't need a real MCP
cluster or Ollama daemon running."""

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.routes.tasks as tasks_module
from app import config as config_module
from app.database import Base
from app.main import app
from planner.plan import PlanStep


@dataclass
class _FakeStepResult:
    step: PlanStep
    tool_result: dict | None
    is_error: bool
    error_message: str | None = None


@dataclass
class _FakeOutcome:
    task: str
    status: str
    message: str
    step_results: list = field(default_factory=list)


class _FakeOrchestrator:
    def __init__(self, outcome: _FakeOutcome) -> None:
        self.outcome = outcome

    async def run_task(self, task: str) -> _FakeOutcome:
        self.outcome.task = task
        return self.outcome


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)

    with TestClient(app) as test_client:
        yield test_client


def test_create_task_returns_outcome_from_orchestrator(client, monkeypatch):
    outcome = _FakeOutcome(
        task="",
        status="completed",
        message="found it",
        step_results=[
            _FakeStepResult(
                step=PlanStep(tool="search.keyword", arguments={"query": "TODO"}),
                tool_result={"matches": []},
                is_error=False,
            )
        ],
    )

    async def fake_get_orchestrator():
        return _FakeOrchestrator(outcome)

    monkeypatch.setattr(tasks_module, "get_orchestrator", fake_get_orchestrator)

    response = client.post("/api/tasks", json={"task": "find TODOs"})

    assert response.status_code == 200
    body = response.json()
    assert body["task"] == "find TODOs"
    assert body["status"] == "completed"
    assert body["steps"][0]["tool"] == "search.keyword"
    assert body["steps"][0]["is_error"] is False


def test_create_task_returns_503_when_orchestrator_unavailable(client, monkeypatch):
    async def fake_get_orchestrator():
        raise ConnectionError("mcp servers not running")

    monkeypatch.setattr(tasks_module, "get_orchestrator", fake_get_orchestrator)

    response = client.post("/api/tasks", json={"task": "find TODOs"})

    assert response.status_code == 503
