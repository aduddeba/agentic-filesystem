"""Implementation behind the Vector MCP server.

`search` reuses `app.search.semantic_search` as-is (the existing, tested hybrid
keyword+vector logic) rather than duplicating it. `insert`/`delete` are plain
`Chunk` CRUD, opening a short-lived `Session` per call via
`app.database.SessionLocal()` -- the same pattern `app/routes/files.py` gets
from FastAPI's `Depends(get_db)`, just without the DI.
"""

from typing import Literal, TypedDict

from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Chunk, FileRecord
from app.search import semantic_search
from tools.embeddings import embed_passages


class SemanticMatchOut(TypedDict):
    path: str
    text: str
    score: float


class SearchOut(TypedDict):
    matches: list[SemanticMatchOut]


def search(query: str, k: int = 10, mode: Literal["hybrid", "vector"] = "hybrid") -> SearchOut:
    """Rank indexed file chunks by embedding similarity to `query`, optionally fused with keyword search."""
    if not query.strip():
        return SearchOut(matches=[])

    db = SessionLocal()
    try:
        matches = semantic_search(db, query, k=k, mode=mode)
        return SearchOut(matches=[SemanticMatchOut(path=m.path, text=m.text, score=m.score) for m in matches])
    finally:
        db.close()


class InsertOut(TypedDict):
    chunk_id: int


def insert(file_path: str, chunk_index: int, text: str) -> InsertOut:
    """Embed `text` and store it as a chunk of the already-indexed file at `file_path`."""
    db = SessionLocal()
    try:
        record = db.scalar(select(FileRecord).where(FileRecord.path == file_path))
        if record is None:
            raise ValueError(f"No indexed file record for path: {file_path}")

        vector = embed_passages([text])[0]
        row = Chunk(file_id=record.id, chunk_index=chunk_index, text=text, embedding=vector)
        db.add(row)
        db.commit()
        db.refresh(row)
        return InsertOut(chunk_id=row.id)
    finally:
        db.close()


class DeleteOut(TypedDict):
    file_path: str
    deleted: int


def delete(file_path: str) -> DeleteOut:
    """Delete every chunk belonging to the file at `file_path`."""
    db = SessionLocal()
    try:
        record = db.scalar(select(FileRecord).where(FileRecord.path == file_path))
        if record is None:
            return DeleteOut(file_path=file_path, deleted=0)

        result = db.execute(sa_delete(Chunk).where(Chunk.file_id == record.id))
        db.commit()
        return DeleteOut(file_path=file_path, deleted=result.rowcount or 0)
    finally:
        db.close()
