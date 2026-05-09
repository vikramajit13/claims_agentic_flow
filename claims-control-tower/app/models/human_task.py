from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HumanTaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HumanTaskType(str, Enum):
    CLAIM_REVIEW = "claim_review"
    FRAUD_REVIEW = "fraud_review"
    PAYMENT_APPROVAL = "payment_approval"
    MISSING_DOCUMENT_REVIEW = "missing_document_review"


class HumanTask(BaseModel):
    id: int = Field(..., description="Unique identifier for the human task")
    claim_id: int = Field(..., description="ID of the claim associated with this task")
    workflow_run_id: int = Field(..., description="ID of the workflow run associated with this task")
    task_type: HumanTaskType = Field(default=HumanTaskType.CLAIM_REVIEW, description="Type of the human task")
    status: HumanTaskStatus = Field(default=HumanTaskStatus.OPEN, description="Current status of the human task")
    assigned_to: str = Field(..., description="ID of the user assigned to the task")
    reason: Optional[str] = Field(None, description="Reason for the task")
    decision: Optional[str] = Field(None, description="Decision made on the task")
    decision_notes: Optional[str] = Field(None, description="Additional notes on the decision")
    created_at: str = Field(..., description="Timestamp when the task was created")
    completed_at: Optional[str] = Field(None, description="Timestamp when the task was completed")
