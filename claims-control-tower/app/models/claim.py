
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_HUMAN_REVIEW = "pending_human_review"
    PENDING_MORE_INFO = "pending_more_info"
    PAYMENT_READY = "payment_ready"
    PAYMENT_BLOCKED = "payment_blocked"
    COMPLETED = "completed"


class Claim(BaseModel):
    id: int = Field(..., description="Unique identifier for the claim")
    claim_number: str = Field(..., description="Unique claim number")
    customer_id: int = Field(..., description="ID of the customer making the claim")
    policy_id: int = Field(..., description="ID of the insurance policy related to the claim")
    claim_type: str = Field(..., description="Type of the claim (e.g., 'auto', 'home', 'health')")
    claim_amount: float = Field(..., description="Amount claimed")
    incident_date: str = Field(..., description="Date of the incident (YYYY-MM-DD)")
    description: str = Field(..., description="Description of the incident")
    status: ClaimStatus = Field(default=ClaimStatus.SUBMITTED, description="Current status of the claim (e.g., 'pending', 'approved', 'rejected')")
    created_at: str = Field(..., description="Timestamp when the claim was created")
    updated_at: str = Field(..., description="Timestamp when the claim was last updated")



