from app.models.payment_instruction import PaymentInstruction
from app.repositories.payment_repository import PaymentRepository


class PaymentAdapter:
    def __init__(self, payment_repo: PaymentRepository | None = None) -> None:
        self.payment_repo = payment_repo or PaymentRepository()

    def create_payment_instruction(
        self,
        claim_id: int,
        workflow_run_id: int,
        amount: float,
        customer_id: int,
    ) -> PaymentInstruction:
        return self.payment_repo.create(
            claim_id=claim_id,
            workflow_run_id=workflow_run_id,
            payee_customer_id=customer_id,
            amount=amount,
        )

    def check_duplicate_payment(self, claim_id: int) -> bool:
        return self.payment_repo.duplicate_exists(claim_id)
