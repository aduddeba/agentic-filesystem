"""REST endpoints for viewing and changing which folder the app manages."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import set_storage_root, settings
from ..database import get_db
from ..indexing import index_pending
from ..repository import reconcile
from ..schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/api")


@router.get("/settings", response_model=SettingsOut)
def get_settings() -> SettingsOut:
    return SettingsOut(storage_root=settings.storage_root)


@router.put("/settings", response_model=SettingsOut)
def update_settings(body: SettingsIn, db: Session = Depends(get_db)) -> SettingsOut:
    target = Path(body.storage_root)
    if not target.is_absolute():
        raise HTTPException(status_code=400, detail=f"Path must be absolute: {body.storage_root}")
    if target.exists() and not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {body.storage_root}")

    target.mkdir(parents=True, exist_ok=True)
    set_storage_root(str(target))

    reconcile(db)
    index_pending(db)

    return SettingsOut(storage_root=settings.storage_root)
