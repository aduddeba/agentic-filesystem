"""Pydantic request/response models for the REST API."""

from typing import Literal

from pydantic import BaseModel


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
