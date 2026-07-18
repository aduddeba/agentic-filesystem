"""Plan / PlanStep / VerificationOutcome -- plain data the Planner produces and consumes.

Live next to the Planner since it's the only thing that constructs them (see
`backend/docs/mcp_architecture.md` #9: "Pydantic dataclasses... live next to
the Protocol that consumes them").
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]


class VerificationOutcome(BaseModel):
    satisfied: bool
    notes: str


class PlanningError(Exception):
    """Raised when the LLM's response can't be parsed into a `Plan`/`VerificationOutcome`.

    Caught by the Orchestrator (not the API route), which turns it into a
    failed `TaskOutcome` instead of a 500.
    """
