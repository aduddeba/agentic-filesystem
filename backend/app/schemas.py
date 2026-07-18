"""Pydantic request/response models for the REST API."""

from typing import Literal

from pydantic import BaseModel, Field


class TreeNodeOut(BaseModel):
    path: str
    name: str
    is_dir: bool
    depth: int
    size: int


class StatsOut(BaseModel):
    file_count: int
    directory_count: int
    total_size: int


class FileContentOut(BaseModel):
    path: str
    content: str


class ContentIn(BaseModel):
    content: str = ""


class CreateIn(BaseModel):
    path: str
    type: Literal["file", "directory"]
    content: str = ""


class RenameIn(BaseModel):
    path: str
    new_path: str


class SearchMatchOut(BaseModel):
    path: str
    line: int
    text: str


class SemanticMatchOut(BaseModel):
    path: str
    text: str
    score: float


class ReindexOut(BaseModel):
    indexed: int
    failed: int


class SettingsOut(BaseModel):
    storage_root: str


class SettingsIn(BaseModel):
    storage_root: str


class TaskIn(BaseModel):
    task: str = ""
    tool: str | None = None
    arguments: dict = Field(default_factory=dict)


class TaskStepOut(BaseModel):
    tool: str
    arguments: dict
    is_error: bool
    result: dict | None = None
    error_message: str | None = None


class TaskOut(BaseModel):
    task: str
    status: Literal["completed", "partial", "failed"]
    message: str
    steps: list[TaskStepOut]
