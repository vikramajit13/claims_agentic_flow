from __future__ import annotations

from pydantic import BaseModel, Field


class ClaimGraphState(BaseModel):
    claim_id: int
    workflow_id: int
    notes: list[str] = Field(default_factory=list)
    hitl_required: bool = True
