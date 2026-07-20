"""MemoryStore tests -- real Postgres (reuses tests/conftest.py's pg_engine, skips if
unreachable, same pattern as every other DB-backed test in this repo). MemoryStore is fully
synchronous (`mcp_architecture.md` #9's MemoryStore Protocol has no `async def`), so no
anyio marker is needed here."""

import pytest
from sqlalchemy.orm import sessionmaker

from memory.store import MemoryStore


@pytest.fixture
def memory_store(pg_engine):
    session_factory = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    return MemoryStore(session_factory)


def test_recent_tasks_returns_most_recent_first(memory_store):
    memory_store.record_task("find TODOs", "found 3 TODOs", [], status="completed")
    memory_store.record_task("search FastAPI", "found nothing", [], status="failed")

    recent = memory_store.recent_tasks()

    assert [r.task for r in recent] == ["search FastAPI", "find TODOs"]
    assert recent[0].status == "failed"
    assert recent[0].summary == "found nothing"


def test_recent_tasks_respects_limit(memory_store):
    for i in range(5):
        memory_store.record_task(f"task {i}", "done", [])

    assert len(memory_store.recent_tasks(limit=2)) == 2


def test_recent_tasks_empty_when_nothing_recorded(memory_store):
    assert memory_store.recent_tasks() == []


def test_record_task_writes_one_file_history_entry_per_delta(memory_store):
    memory_store.record_task("write two files", "wrote them", ["notes.txt", "todo.txt"], status="completed")

    assert len(memory_store.file_history("notes.txt")) == 1
    assert len(memory_store.file_history("todo.txt")) == 1


def test_file_history_is_empty_for_an_untouched_path(memory_store):
    assert memory_store.file_history("never-touched.txt") == []


def test_record_task_with_no_file_deltas_writes_no_history(memory_store):
    memory_store.record_task("just a search", "found stuff", [])

    assert memory_store.file_history("anything.txt") == []


def test_preferences_returns_empty_dict_since_nothing_writes_to_it_yet(memory_store):
    assert memory_store.preferences() == {}
