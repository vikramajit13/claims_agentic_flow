from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.enums import HumanDecision


class HumanTaskStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class HumanTaskType(str, Enum):
    CLAIM_REVIEW = "CLAIM_REVIEW"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    PAYMENT_REVIEW = "PAYMENT_REVIEW"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"


class HumanTaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class HumanTask(BaseModel):
    id: int = Field(..., description="Unique identifier for the human task")
    claim_id: int = Field(..., description="ID of the claim associated with this task")
    workflow_run_id: int = Field(..., description="ID of the workflow run associated with this task")
    task_type: HumanTaskType = Field(default=HumanTaskType.CLAIM_REVIEW, description="Type of the human task")
    status: HumanTaskStatus = Field(default=HumanTaskStatus.OPEN, description="Current status of the human task")
    priority: HumanTaskPriority = Field(default=HumanTaskPriority.MEDIUM, description="Task priority")
    assigned_to: Optional[str] = Field(None, description="ID of the user assigned to the task")
    created_reason: Optional[str] = Field(None, description="Reason for creating the task")
    risk_factors: list[str] = Field(default_factory=list, description="Risk factors requiring review")
    recommended_decision: Optional[str] = Field(None, description="System recommended decision")
    recommended_payout_amount: Optional[float] = Field(None, description="System recommended payout")
    adjuster_briefing: dict | None = Field(default=None, description="Structured adjuster briefing payload")
    reviewer_decision: Optional[HumanDecision] = Field(None, description="Decision made by reviewer")
    reviewer_notes: Optional[str] = Field(None, description="Additional reviewer notes")
    reviewer_modified_payout_amount: Optional[float] = Field(None, description="Modified payout amount from reviewer")
    completed_by: Optional[str] = Field(None, description="Reviewer identifier")
    created_at: str = Field(..., description="Timestamp when the task was created")
    updated_at: str = Field(..., description="Timestamp when the task was last updated")
    completed_at: Optional[str] = Field(None, description="Timestamp when the task was completed")
