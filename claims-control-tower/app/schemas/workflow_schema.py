from typing import Optional

from pydantic import BaseModel, Field

from app.enums import FraudRiskLevel, RecommendationDecision
from app.models.workflow_event import WorkflowEvent
from app.models.workflow_run import WorkflowRun


class CoverageValidationResult(BaseModel):
    is_valid: bool
    reasons: list[str] = Field(default_factory=list)
    policy_id: Optional[int] = None
    coverage_limit: Optional[float] = None


class DocumentValidationResult(BaseModel):
    is_valid: bool
    required_documents: list[str] = Field(default_factory=list)
    provided_documents: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class FraudRiskResult(BaseModel):
    risk_score: int
    risk_level: FraudRiskLevel
    risk_factors: list[str] = Field(default_factory=list)


class RiskSignalResult(BaseModel):
    requires_human_review: bool
    reason: str
    risk_factors: list[str] = Field(default_factory=list)
    recommended_action: str = "NONE"


class AdjudicationRecommendation(BaseModel):
    recommendation: RecommendationDecision
    reason: str
    recommended_amount: float
    requires_human_review: bool
    risk_factors: list[str] = Field(default_factory=list)
    recommended_action: str | None = None


class WorkflowExecutionResponse(BaseModel):
    workflow_run: WorkflowRun
    recommendation: Optional[AdjudicationRecommendation] = None
    payment_instruction_id: Optional[int] = None
    human_task_id: Optional[int] = None
    claim_status: Optional[str] = None
    final_decision: Optional[str] = None
    final_approved_amount: Optional[float] = None


class WorkflowRunDetail(BaseModel):
    workflow_run: WorkflowRun
    events: list[WorkflowEvent] = Field(default_factory=list)


class WorkflowPauseRequest(BaseModel):
    reason: Optional[str] = None
