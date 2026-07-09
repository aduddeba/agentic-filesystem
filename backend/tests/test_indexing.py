from sqlalchemy import select

from app.indexing import index_file, index_pending, reindex_all
from app.models import Chunk, FileRecord


def _make_record(pg_session, tmp_path, path: str, content: str) -> FileRecord:
    (tmp_path / path).write_text(content, encoding="utf-8")
    record = FileRecord(path=path, name=path.split("/")[-1], is_dir=False, size=len(content))
    pg_session.add(record)
    pg_session.commit()
    return record


def test_index_file_populates_metadata(pg_session, tmp_path, monkeypatch):
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    record = _make_record(pg_session, tmp_path, "note.txt", "hello world, this is a test file")

    index_file(pg_session, record)

    assert record.word_count == 7
    assert record.char_count == len("hello world, this is a test file")
    assert record.mime_type == "text/plain"
    assert record.indexed_at is not None
    assert record.index_error is None


def test_index_file_creates_chunks_with_correct_dimension(pg_session, tmp_path, monkeypatch):
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    words = " ".join(f"word{i}" for i in range(500))
    record = _make_record(pg_session, tmp_path, "big.txt", words)

    index_file(pg_session, record)

    chunks = pg_session.scalars(select(Chunk).where(Chunk.file_id == record.id)).all()
    assert len(chunks) == 3
    assert all(len(c.embedding) == 384 for c in chunks)


def test_index_file_replaces_old_chunks_on_reindex(pg_session, tmp_path, monkeypatch):
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    record = _make_record(pg_session, tmp_path, "note.txt", "original content here")
    index_file(pg_session, record)
    first_chunk_ids = {c.id for c in pg_session.scalars(select(Chunk).where(Chunk.file_id == record.id)).all()}

    (tmp_path / "note.txt").write_text("completely different content now", encoding="utf-8")
    index_file(pg_session, record)

    second_chunks = pg_session.scalars(select(Chunk).where(Chunk.file_id == record.id)).all()
    second_chunk_ids = {c.id for c in second_chunks}
    assert first_chunk_ids.isdisjoint(second_chunk_ids)
    assert second_chunks[0].text == "completely different content now"


def test_index_file_skips_binary_extension_without_error(pg_session, tmp_path, monkeypatch):
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nnot a real png")
    record = FileRecord(path="image.png", name="image.png", is_dir=False, size=20)
    pg_session.add(record)
    pg_session.commit()

    index_file(pg_session, record)

    assert record.index_error is None
    assert record.indexed_at is not None
    chunks = pg_session.scalars(select(Chunk).where(Chunk.file_id == record.id)).all()
    assert chunks == []


def test_index_pending_only_indexes_unindexed_records(pg_session, tmp_path, monkeypatch):
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    already_indexed = _make_record(pg_session, tmp_path, "old.txt", "old content")
    index_file(pg_session, already_indexed)
    old_indexed_at = already_indexed.indexed_at

    fresh = _make_record(pg_session, tmp_path, "new.txt", "brand new content")

    index_pending(pg_session)

    assert already_indexed.indexed_at == old_indexed_at
    assert fresh.indexed_at is not None


def test_reindex_all_reindexes_every_record_unconditionally(pg_session, tmp_path, monkeypatch):
    from app import config as config_module

    monkeypatch.setattr(config_module.settings, "storage_root", str(tmp_path))
    record = _make_record(pg_session, tmp_path, "note.txt", "original")
    index_file(pg_session, record)
    first_indexed_at = record.indexed_at

    # simulate an out-of-band edit: content changes on disk without going through the API
    (tmp_path / "note.txt").write_text("edited outside the app", encoding="utf-8")

    result = reindex_all(pg_session)

    assert result == {"indexed": 1, "failed": 0}
    assert record.indexed_at > first_indexed_at
    chunk = pg_session.scalar(select(Chunk).where(Chunk.file_id == record.id))
    assert chunk.text == "edited outside the app"
