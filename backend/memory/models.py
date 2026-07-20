"""ORM models for Memory -- plain SQLAlchemy, never touched via MCP (`mcp_architecture.md` #1:
"Memory ... plain Python -- never via MCP"). Shares `app.database.Base` rather than a separate
metadata/engine so the existing `Base.metadata.create_all()` in `app/main.py`'s lifespan (the
de facto dev/test schema source of truth -- see the Alembic migration below) picks these up
for free, exactly like `FileRecord`/`Chunk` already do.

No standalone `Summary` model: the design doc's folder-tree comment names one, but no
`MemoryStore` method returns or needs it separately from `TaskRecord.summary`. Deliberate
deviation, not an oversight.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskRecord(Base):
    __tablename__ = "task_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class FileHistoryEntry(Base):
    __tablename__ = "file_history_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task_records.id", ondelete="CASCADE"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
