"""Plain, text-ready views handed to the Planner -- decoupled from the ORM the same way
`ToolCatalog.as_planner_context()` renders tools as a string blob rather than raw objects."""

from pydantic import BaseModel, Field


class MemoryContext(BaseModel):
    recent_tasks: list[str] = Field(default_factory=list)
    preferences: dict[str, str] = Field(default_factory=dict)
