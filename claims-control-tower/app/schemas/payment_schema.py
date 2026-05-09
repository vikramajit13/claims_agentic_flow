from pydantic import BaseModel, Field

from app.models.payment_instruction import PaymentGuardrailStatus, PaymentInstruction


class PaymentGuardrailResult(BaseModel):
    guardrail_status: PaymentGuardrailStatus
    reasons: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.guardrail_status == PaymentGuardrailStatus.PASSED


class PaymentInstructionResponse(BaseModel):
    payment_instruction: PaymentInstruction
