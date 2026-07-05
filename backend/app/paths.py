"""Safe resolution of API-supplied relative paths against the storage root."""

from pathlib import Path

from fastapi import HTTPException

from .config import settings


def resolve_path(relative: str) -> Path:
    """Resolve `relative` against the storage root, rejecting escapes.

    Raises HTTP 400 if the resolved path is outside `settings.storage_root`
    (e.g. via `..` segments or an absolute path).
    """
    cleaned = (relative or "").strip()
    if cleaned.startswith("/") or Path(cleaned).is_absolute():
        raise HTTPException(status_code=400, detail=f"Invalid path: {relative}")

    root = Path(settings.storage_root).resolve()
    candidate = (root / cleaned.strip("/")).resolve()

    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail=f"Invalid path: {relative}")

    return candidate


def to_relative(path: Path) -> str:
    root = Path(settings.storage_root).resolve()
    return path.resolve().relative_to(root).as_posix()
