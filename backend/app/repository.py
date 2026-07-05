"""Keeps the `files` table in sync with what's actually on disk."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tools.filesystem import walk

from .config import settings
from .models import FileRecord
from .schemas import StatsOut


def reconcile(db: Session) -> None:
    """Make the `files` table match the storage root exactly.

    Called after every mutating request (and once at startup) so the DB
    never has to hand-track renames/deletes of nested paths — it just
    re-derives itself from the (small, local) directory tree each time.
    """
    entries = walk(settings.storage_root)
    on_disk = {entry.path for entry in entries}

    existing = {record.path: record for record in db.scalars(select(FileRecord)).all()}

    for entry in entries:
        record = existing.get(entry.path)
        if record is None:
            db.add(FileRecord(path=entry.path, name=entry.name, is_dir=entry.is_dir, size=entry.size))
        elif record.is_dir != entry.is_dir or record.size != entry.size or record.name != entry.name:
            record.name = entry.name
            record.is_dir = entry.is_dir
            record.size = entry.size

    for path, record in existing.items():
        if path not in on_disk:
            db.delete(record)

    db.commit()


def get_stats(db: Session) -> StatsOut:
    file_count = db.scalar(select(func.count()).select_from(FileRecord).where(FileRecord.is_dir.is_(False))) or 0
    directory_count = db.scalar(select(func.count()).select_from(FileRecord).where(FileRecord.is_dir.is_(True))) or 0
    total_size = db.scalar(select(func.coalesce(func.sum(FileRecord.size), 0))) or 0

    return StatsOut(file_count=file_count, directory_count=directory_count, total_size=total_size)
