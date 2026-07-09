"""REST endpoints for browsing and editing files under the storage root."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from tools.filesystem import delete as delete_tool
from tools.filesystem import make_directory
from tools.filesystem import read as read_tool
from tools.filesystem import rename as rename_tool
from tools.filesystem import search as search_tool
from tools.filesystem import walk
from tools.filesystem import write as write_tool

from ..config import settings
from ..database import get_db
from ..indexing import index_file, index_pending, reindex_all
from ..models import FileRecord
from ..paths import resolve_path, to_relative
from ..repository import get_stats, reconcile
from ..schemas import (
    ContentIn,
    CreateIn,
    FileContentOut,
    ReindexOut,
    RenameIn,
    SearchMatchOut,
    SemanticMatchOut,
    StatsOut,
    TreeNodeOut,
)
from ..search import semantic_search

router = APIRouter(prefix="/api")


def _node_out(target: Path, is_dir: bool) -> TreeNodeOut:
    relative = to_relative(target)
    size = 0 if is_dir else target.stat().st_size
    return TreeNodeOut(path=relative, name=target.name, is_dir=is_dir, depth=relative.count("/"), size=size)


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/files/tree", response_model=list[TreeNodeOut])
def get_tree() -> list[TreeNodeOut]:
    entries = walk(settings.storage_root)
    return [
        TreeNodeOut(path=e.path, name=e.name, is_dir=e.is_dir, depth=e.depth, size=e.size) for e in entries
    ]


@router.get("/files/stats", response_model=StatsOut)
def get_file_stats(db: Session = Depends(get_db)) -> StatsOut:
    return get_stats(db)


@router.get("/files/content", response_model=FileContentOut)
def get_file_content(path: str = Query(...)) -> FileContentOut:
    target = resolve_path(path)
    try:
        content = read_tool(str(target))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}") from None
    return FileContentOut(path=path, content=content)


@router.post("/files", response_model=TreeNodeOut, status_code=201)
def create_entry(body: CreateIn, db: Session = Depends(get_db)) -> TreeNodeOut:
    target = resolve_path(body.path)
    if target.exists():
        raise HTTPException(status_code=409, detail=f"Path already exists: {body.path}")

    is_dir = body.type == "directory"
    if is_dir:
        make_directory(str(target))
    else:
        write_tool(str(target), body.content)

    reconcile(db)
    if not is_dir:
        record = db.scalar(select(FileRecord).where(FileRecord.path == to_relative(target)))
        index_file(db, record)
    return _node_out(target, is_dir)


@router.put("/files/content", response_model=TreeNodeOut)
def update_file_content(body: ContentIn, path: str = Query(...), db: Session = Depends(get_db)) -> TreeNodeOut:
    target = resolve_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    write_tool(str(target), body.content)
    reconcile(db)
    record = db.scalar(select(FileRecord).where(FileRecord.path == to_relative(target)))
    index_file(db, record)
    return _node_out(target, is_dir=False)


@router.delete("/files", status_code=204, response_model=None)
def delete_entry(path: str = Query(...), db: Session = Depends(get_db)) -> None:
    target = resolve_path(path)
    try:
        delete_tool(str(target))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {path}") from None

    reconcile(db)


@router.patch("/files", response_model=TreeNodeOut)
def rename_entry(body: RenameIn, db: Session = Depends(get_db)) -> TreeNodeOut:
    src = resolve_path(body.path)
    dst = resolve_path(body.new_path)
    is_dir = src.is_dir()

    try:
        rename_tool(str(src), str(dst))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {body.path}") from None
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Path already exists: {body.new_path}") from None

    reconcile(db)
    index_pending(db)
    return _node_out(dst, is_dir)


@router.get("/files/search", response_model=list[SearchMatchOut])
def search_files(q: str = Query(...), path: str = Query("")) -> list[SearchMatchOut]:
    if not q.strip():
        return []
    root = resolve_path(path)
    matches = search_tool(q, root=str(root))
    return [SearchMatchOut(path=to_relative(Path(m.file)), line=m.line, text=m.text) for m in matches]


@router.get("/files/search/semantic", response_model=list[SemanticMatchOut])
def search_semantic(
    q: str = Query(...),
    k: int = Query(10, ge=1, le=50),
    mode: Literal["hybrid", "vector"] = Query("hybrid"),
    db: Session = Depends(get_db),
) -> list[SemanticMatchOut]:
    if not q.strip():
        return []
    return semantic_search(db, q, k=k, mode=mode)


@router.post("/files/reindex", response_model=ReindexOut)
def reindex(db: Session = Depends(get_db)) -> ReindexOut:
    reconcile(db)
    return ReindexOut(**reindex_all(db))
