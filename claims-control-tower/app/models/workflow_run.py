from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowRunStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_FOR_HUMAN = "waiting_for_human"
    WAITING_FOR_INFO = "waiting_for_info"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowRunStep(str, Enum):
    CLAIM_INTAKE = "claim_intake"
    COVERAGE_VALIDATION = "coverage_validation"
    EVIDENCE_VALIDATION = "evidence_validation"
    FRAUD_RISK_CHECK = "fraud_risk_check"
    ADJUDICATION = "adjudication"
    HUMAN_REVIEW = "human_review"
    PAYMENT_GUARDRAIL = "payment_guardrail"
    PAYMENT_INSTRUCTION = "payment_instruction"
    FINAL_AUDIT = "final_audit"
    COMPLETED = "completed"


class WorkflowRun(BaseModel):
    id: int = Field(..., description="Unique identifier for the workflow run")
    claim_id: int = Field(..., description="ID of the claim associated with this workflow run")
    workflow_name: str = Field(..., description="Name of the workflow being executed")
    status: WorkflowRunStatus = Field(..., description="Current status of the workflow run")
    current_step: WorkflowRunStep = Field(..., description="Current step being executed")
    started_at: Optional[str] = Field(None, description="Timestamp when the workflow run started")
    completed_at: Optional[str] = Field(None, description="Timestamp when the workflow run completed")
    last_error: Optional[str] = Field(None, description="Error message if the workflow run failed")
    created_at: Optional[str] = Field(None, description="Timestamp when the workflow run was created")
    updated_at: Optional[str] = Field(None, description="Timestamp when the workflow run was last updated")
