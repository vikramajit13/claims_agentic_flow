from __future__ import annotations

from datetime import datetime

from app.database import get_store
from app.models.payment_instruction import PaymentGuardrailStatus, PaymentInstruction, PaymentInstructionStatus


class PaymentRepository:
    def __init__(self) -> None:
        self.store = get_store()

    def create(
        self,
        claim_id: int,
        workflow_run_id: int,
        payee_customer_id: int,
        amount: float,
        currency: str = "AUD",
        guardrail_status: PaymentGuardrailStatus = PaymentGuardrailStatus.PASSED,
    ) -> PaymentInstruction:
        now = _now_iso()
        payment_instruction = PaymentInstruction(
            id=self.store.next_id("payment_instructions"),
            claim_id=claim_id,
            workflow_run_id=workflow_run_id,
            payee_customer_id=payee_customer_id,
            amount=amount,
            currency=currency,
            status=PaymentInstructionStatus.READY_FOR_PAYMENT,
            guardrail_status=guardrail_status,
            payment_reference=f"PAY-{claim_id}-{self.store.counters['payment_instructions']}",
            created_at=now,
            updated_at=now,
        )
        self.store.payment_instructions[payment_instruction.id] = payment_instruction
        return payment_instruction

    def get(self, payment_instruction_id: int) -> PaymentInstruction:
        return self.store.payment_instructions[payment_instruction_id]

    def list(self) -> list[PaymentInstruction]:
        return list(self.store.payment_instructions.values())

    def get_by_claim(self, claim_id: int) -> list[PaymentInstruction]:
        return [payment for payment in self.list() if payment.claim_id == claim_id]

    def duplicate_exists(self, claim_id: int) -> bool:
        return any(payment.claim_id == claim_id for payment in self.list())


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
