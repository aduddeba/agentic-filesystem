"""MemoryStore -- SQLAlchemy-backed, called directly by the Orchestrator (never through
MCPClientPool/ToolCatalog; see `models.py`'s docstring). Each method opens and closes its
own short session, matching the per-request `get_db()` pattern used elsewhere in `app/`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .models import FileHistoryEntry, Preference, TaskRecord

# Tool namespaces/actions that mutate the filesystem -- used by the Orchestrator to derive
# `file_deltas` from a run's StepResults; kept here since it's what record_task() consumes.
MUTATING_FILESYSTEM_TOOLS = frozenset(
    {"filesystem.write", "filesystem.delete", "filesystem.mkdir", "filesystem.rename"}
)


class MemoryStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def recent_tasks(self, limit: int = 10) -> list[TaskRecord]:
        with self._session_factory() as session:
            # order by id as well as created_at -- two tasks recorded within the same
            # timestamp tick would otherwise sort arbitrarily.
            stmt = select(TaskRecord).order_by(TaskRecord.created_at.desc(), TaskRecord.id.desc()).limit(limit)
            return list(session.scalars(stmt))

    def preferences(self) -> dict[str, str]:
        with self._session_factory() as session:
            return {p.key: p.value for p in session.scalars(select(Preference))}

    def record_task(self, task: str, summary: str, file_deltas: list[str], status: str = "unknown") -> None:
        with self._session_factory() as session:
            record = TaskRecord(task=task, summary=summary, status=status)
            session.add(record)
            session.flush()
            for path in file_deltas:
                session.add(FileHistoryEntry(task_id=record.id, path=path))
            session.commit()

    def file_history(self, path: str) -> list[FileHistoryEntry]:
        with self._session_factory() as session:
            stmt = (
                select(FileHistoryEntry)
                .where(FileHistoryEntry.path == path)
                .order_by(FileHistoryEntry.created_at.desc(), FileHistoryEntry.id.desc())
            )
            return list(session.scalars(stmt))
