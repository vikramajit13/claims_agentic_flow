
from pydantic import BaseModel, Field
from typing import Optional
from enum import StrEnum   

class PaymentInstructionStatus(StrEnum):
    PENDING = "pending"
    READY_FOR_PAYMENT = "ready_for_payment"
    BLOCKED = "blocked"
    SENT = "sent"
    FAILED = "failed"

class PaymentGuardrailStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_APPROVAL = "requires_approval"

class PaymentInstruction(BaseModel):
    id: int = Field(..., description="Unique identifier for the payment instruction")
    claim_id: int = Field(..., description="ID of the claim associated with this payment instruction")
    workflow_run_id: int = Field(..., description="ID of the workflow run associated with this payment instruction")
    payee_customer_id: int = Field(..., description="ID of the payee customer")
    amount: float = Field(..., description="Amount to be paid")
    currency: str = Field(..., description="Currency of the payment")
    status: PaymentInstructionStatus = Field(default=PaymentInstructionStatus.PENDING, description="Current status of the payment instruction")
    guardrail_status: PaymentGuardrailStatus = Field(default=PaymentGuardrailStatus.REQUIRES_APPROVAL, description="Status of the payment guardrail")
    payment_reference: str = Field(..., description="Reference ID for the payment")
    created_at: str = Field(..., description="Timestamp when the payment instruction was created")
    updated_at: str = Field(..., description="Timestamp when the payment instruction was last updated")