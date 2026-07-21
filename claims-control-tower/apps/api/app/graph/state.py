from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import ClaimDocumentState
from app.schemas.workflow import ClaimWorkflowState


class ClaimGraphState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    claim_id: int
    graph_name: str = "claim_review_graph"
    graph_version: str = "v1"
    graph_run_id: str | None = None
    notes: list[str] = Field(default_factory=list)
    hitl_required: bool = False
    claim_documents: list[ClaimDocumentState] = Field(default_factory=list)
    claim_status: str = "draft"
    claim_amount: float | None = None
    claim_type: str | None = None
    incident_date: str | None = None
    workflow_state: ClaimWorkflowState | None = None
    claim_description: str | None = None
    risk_score: int = 0
    risk_level: str = "LOW"
    risk_factors: list[str] = Field(default_factory=list)
    human_review_request: dict | None = None
    human_review_response: dict | None = None
    human_review_decision: str | None = None
    human_review_notes: str | None = None
    errors: list[str] = Field(default_factory=list)
    current_step: str = "graph_bootstrap"
    execution_plan: list[str] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    correlation_id: str | None = None
