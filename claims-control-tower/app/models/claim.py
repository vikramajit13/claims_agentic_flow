from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
    claim_type: str = Field(..., description="Type of the claim")
    claim_amount: float = Field(..., description="Amount claimed")
    incident_date: str = Field(..., description="Date of the incident (YYYY-MM-DD)")
    description: str = Field(..., description="Description of the incident")
    previous_claim_id: Optional[int] = Field(default=None, description="Linked prior claim identifier")
    status: ClaimStatus = Field(default=ClaimStatus.SUBMITTED, description="Current status")
    created_at: str = Field(..., description="Timestamp when the claim was created")
    updated_at: str = Field(..., description="Timestamp when the claim was last updated")
