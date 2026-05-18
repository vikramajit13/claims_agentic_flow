from typing import Optional

from pydantic import BaseModel, Field

from app.enums import HumanDecision
from app.models.human_task import HumanTask
from app.models.claim import Claim
from app.models.claim_document import ClaimDocument
from app.schemas.workflow_schema import WorkflowExecutionResponse


class HumanTaskAssignRequest(BaseModel):
    assigned_to: str


class HumanTaskDecisionRequest(BaseModel):
    decision: HumanDecision
    decision_notes: Optional[str] = None
    approved_amount: Optional[float] = Field(None, gt=0)
    completed_by: str


class HumanTaskCompletionResponse(BaseModel):
    task: HumanTask
    workflow_result: WorkflowExecutionResponse


class HumanTaskListItem(BaseModel):
    task_id: int
    claim_id: int
    claim_number: str
    task_type: str
    priority: str
    status: str
    created_reason: Optional[str] = None
    risk_factors: list[str] = Field(default_factory=list)
    recommended_payout_amount: Optional[float] = None
    created_at: str


class HumanTaskRecommendationView(BaseModel):
    system_decision: Optional[str] = None
    recommended_payout_amount: Optional[float] = None
    reason: Optional[str] = None


class HumanTaskDetailResponse(BaseModel):
    task_id: int
    task_type: str
    status: str
    priority: str
    claim: Claim
    risk_factors: list[str] = Field(default_factory=list)
    documents: list[ClaimDocument] = Field(default_factory=list)
    recommendation: HumanTaskRecommendationView
    adjuster_briefing: dict | None = None
