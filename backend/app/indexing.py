"""Keeps chunk embeddings and extracted metadata in sync with file contents."""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from tools.documents import chunk_text, extract_metadata
from tools.embeddings import embed_passages
from tools.filesystem import read as read_tool

from .models import Chunk, FileRecord
from .paths import resolve_path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Extensions that are never worth reading as text -- read_tool() would just
# produce garbage/mojibake for these. Everything else (including unrecognized
# code/config/text extensions) is treated as indexable, matching read_tool()'s
# own "unknown suffix -> read as UTF-8" fallback.
_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".woff", ".woff2", ".ttf", ".otf",
    ".pyc", ".class", ".o",
}


def index_file(db: Session, record: FileRecord) -> None:
    """(Re)compute metadata and chunk embeddings for a single file record."""
    absolute = resolve_path(record.path)

    if absolute.suffix.lower() in _BINARY_EXTENSIONS:
        record.index_error = None
        record.indexed_at = _utcnow()
        db.execute(delete(Chunk).where(Chunk.file_id == record.id))
        db.commit()
        return

    try:
        text = read_tool(str(absolute))
    except Exception as exc:  # noqa: BLE001 - any parse failure should be recorded, not raised
        record.index_error = str(exc)
        record.indexed_at = _utcnow()
        db.commit()
        return

    meta = extract_metadata(str(absolute), text)
    record.mime_type = meta.mime_type
    record.word_count = meta.word_count
    record.char_count = meta.char_count
    record.index_error = None

    db.execute(delete(Chunk).where(Chunk.file_id == record.id))

    pieces = chunk_text(text)
    if pieces:
        vectors = embed_passages([piece.text for piece in pieces])
        for piece, vector in zip(pieces, vectors):
            db.add(Chunk(file_id=record.id, chunk_index=piece.index, text=piece.text, embedding=vector))

    record.indexed_at = _utcnow()
    db.commit()


def index_pending(db: Session) -> None:
    """Index every file record that has never been indexed.

    After `reconcile()`, this is exactly the set of records it just created --
    new files, and every record on a renamed/moved path (reconcile keys by
    path, so a rename produces a fresh record with a fresh id).
    """
    pending = db.scalars(
        select(FileRecord).where(FileRecord.is_dir.is_(False), FileRecord.indexed_at.is_(None))
    ).all()
    for record in pending:
        index_file(db, record)


def reindex_all(db: Session) -> dict[str, int]:
    """Force re-index every file record, regardless of prior indexing state.

    Used for backfilling files that already existed on disk, or that were
    edited outside the app (no filesystem watcher exists yet -- see Phase 4).
    """
    records = db.scalars(select(FileRecord).where(FileRecord.is_dir.is_(False))).all()
    indexed = failed = 0
    for record in records:
        index_file(db, record)
        if record.index_error:
            failed += 1
        else:
            indexed += 1
    return {"indexed": indexed, "failed": failed}
