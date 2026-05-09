from app.config import settings
from app.models.claim import Claim, ClaimStatus
from app.models.policy import Policy
from app.schemas.payment_schema import PaymentGuardrailResult
from app.schemas.workflow_schema import AdjudicationRecommendation
from app.services.payment_adapter import PaymentAdapter


class PaymentGuardrailService:
    def __init__(self, payment_adapter: PaymentAdapter | None = None) -> None:
        self.payment_adapter = payment_adapter or PaymentAdapter()

    def validate(
        self,
        claim: Claim,
        policy: Policy,
        recommendation: AdjudicationRecommendation,
        has_human_approval: bool = False,
    ) -> PaymentGuardrailResult:
        reasons: list[str] = []
        payment_amount = recommendation.recommended_amount

        if recommendation.recommendation.value != "APPROVE":
            reasons.append("Claim must be approved before payment instruction")
        if payment_amount != recommendation.recommended_amount:
            reasons.append("Payment amount must match approved amount")
        if payment_amount > policy.coverage_limit:
            reasons.append("Payment amount must not exceed policy coverage limit")
        if payment_amount > settings.payment_approval_threshold and not has_human_approval:
            reasons.append("Payment amount above threshold requires human approval")
        if self.payment_adapter.check_duplicate_payment(claim.id):
            reasons.append("Duplicate payment instruction must not already exist")
        if claim.customer_id != policy.customer_id:
            reasons.append("Payee must match policy customer")
        if claim.status not in {ClaimStatus.APPROVED, ClaimStatus.PENDING_HUMAN_REVIEW} and not has_human_approval:
            reasons.append("Claim must be approved before payment instruction")

        if reasons:
            return PaymentGuardrailResult(guardrail_status="failed", reasons=reasons)

        return PaymentGuardrailResult(guardrail_status="passed", reasons=[])
