from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.models.claim import Claim, ClaimStatus
from app.models.claim_document import ClaimDocument, DocumentType
from app.models.policy import Policy
from app.repositories.claim_repository import ClaimRepository
from app.repositories.policy_repository import PolicyRepository
from app.services.business_guardrails.guardrail_config import GuardrailConfig
from app.services.business_guardrails.guardrail_models import (
    GuardrailCategory,
    GuardrailDecision,
    GuardrailEvaluationSummary,
    GuardrailResult,
    GuardrailSeverity,
)
from app.services.claim_service import ClaimService


class BusinessGuardrailService:
    def __init__(
        self,
        claim_repository: ClaimRepository | None = None,
        policy_repository: PolicyRepository | None = None,
        claim_service: ClaimService | None = None,
    ) -> None:
        self.claim_repository = claim_repository or ClaimRepository()
        self.policy_repository = policy_repository or PolicyRepository()
        self.claim_service = claim_service or ClaimService(self.claim_repository)

    def evaluate_pre_adjudication(self, claim_id: int) -> GuardrailEvaluationSummary:
        claim = self.claim_repository.get(claim_id)
        policy = self.policy_repository.get(claim.policy_id)
        documents = self.claim_service.get_claim_documents(claim_id)
        results = [
            self.check_policy_active(policy),
            self.check_early_claim_after_policy_start(claim, policy),
            self.check_incident_within_coverage_period(claim, policy),
            self.check_claim_amount_threshold(claim),
            self.check_invoice_date_not_before_incident(claim, documents),
            self.check_repeat_claims(claim),
            self.check_prior_rejected_claim(claim),
        ]
        return self._summarise(results)

    def evaluate_pre_payment(
        self,
        claim_id: int,
        approved_amount: Decimal,
        final_payout_amount: Decimal,
        human_approval_present: bool,
        is_high_risk: bool,
    ) -> GuardrailEvaluationSummary:
        claim = self.claim_repository.get(claim_id)
        policy = self.policy_repository.get(claim.policy_id)
        results = [
            self.check_payout_near_policy_limit(policy, final_payout_amount),
            self.check_final_payout_not_above_approved_amount(approved_amount, final_payout_amount),
            self.check_high_risk_payment_has_human_approval(is_high_risk, human_approval_present),
        ]
        return self._summarise(results)

    def check_policy_active(self, policy: Policy) -> GuardrailResult:
        if policy.status.lower() != "active":
            return GuardrailResult(
                code="POLICY_NOT_ACTIVE",
                category=GuardrailCategory.POLICY,
                decision=GuardrailDecision.BLOCK,
                severity=GuardrailSeverity.CRITICAL,
                message="Policy is not active",
                details={"policy_id": policy.id, "policy_status": policy.status},
            )
        return GuardrailResult(
            code="POLICY_ACTIVE",
            category=GuardrailCategory.POLICY,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Policy is active",
        )

    def check_early_claim_after_policy_start(self, claim: Claim, policy: Policy) -> GuardrailResult:
        days_since_policy_start = (date.fromisoformat(claim.incident_date) - date.fromisoformat(policy.active_from)).days
        if 0 <= days_since_policy_start <= GuardrailConfig.EARLY_CLAIM_DAYS:
            return GuardrailResult(
                code="EARLY_CLAIM_AFTER_POLICY_START",
                category=GuardrailCategory.FRAUD_RISK,
                decision=GuardrailDecision.REVIEW_REQUIRED,
                severity=GuardrailSeverity.HIGH,
                message=f"Incident occurred {days_since_policy_start} days after policy start",
                details={
                    "policy_start_date": policy.active_from,
                    "incident_date": claim.incident_date,
                    "days_since_policy_start": days_since_policy_start,
                    "threshold_days": GuardrailConfig.EARLY_CLAIM_DAYS,
                },
            )
        return GuardrailResult(
            code="EARLY_CLAIM_AFTER_POLICY_START",
            category=GuardrailCategory.FRAUD_RISK,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Incident did not occur within early-claim review window",
        )

    def check_incident_within_coverage_period(self, claim: Claim, policy: Policy) -> GuardrailResult:
        incident_date = date.fromisoformat(claim.incident_date)
        if not (date.fromisoformat(policy.active_from) <= incident_date <= date.fromisoformat(policy.active_to)):
            return GuardrailResult(
                code="INCIDENT_OUTSIDE_COVERAGE_PERIOD",
                category=GuardrailCategory.POLICY,
                decision=GuardrailDecision.BLOCK,
                severity=GuardrailSeverity.CRITICAL,
                message="Incident date is outside the policy coverage period",
                details={
                    "incident_date": claim.incident_date,
                    "policy_active_from": policy.active_from,
                    "policy_active_to": policy.active_to,
                },
            )
        return GuardrailResult(
            code="INCIDENT_WITHIN_COVERAGE_PERIOD",
            category=GuardrailCategory.POLICY,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Incident date is within policy coverage period",
        )

    def check_claim_amount_threshold(self, claim: Claim) -> GuardrailResult:
        threshold = GuardrailConfig.LARGE_CLAIM_AMOUNT_THRESHOLD
        if Decimal(str(claim.claim_amount)) >= threshold:
            return GuardrailResult(
                code="CLAIM_AMOUNT_ABOVE_REVIEW_THRESHOLD",
                category=GuardrailCategory.CLAIM,
                decision=GuardrailDecision.REVIEW_REQUIRED,
                severity=GuardrailSeverity.MEDIUM,
                message="Claim amount exceeds manual review threshold",
                details={"claim_amount": str(claim.claim_amount), "threshold": str(threshold)},
            )
        return GuardrailResult(
            code="CLAIM_AMOUNT_ABOVE_REVIEW_THRESHOLD",
            category=GuardrailCategory.CLAIM,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Claim amount is below manual review threshold",
        )

    def check_invoice_date_not_before_incident(self, claim: Claim, documents: list[ClaimDocument]) -> GuardrailResult:
        incident_date = date.fromisoformat(claim.incident_date)
        for document in documents:
            if document.document_type != DocumentType.INVOICE:
                continue
            invoice_date = document.document_metadata.get("invoice_date")
            if not invoice_date:
                continue
            parsed_invoice_date = date.fromisoformat(invoice_date)
            if parsed_invoice_date < incident_date:
                return GuardrailResult(
                    code="INVOICE_DATE_BEFORE_INCIDENT",
                    category=GuardrailCategory.FRAUD_RISK,
                    decision=GuardrailDecision.REVIEW_REQUIRED,
                    severity=GuardrailSeverity.HIGH,
                    message=f"Invoice date {invoice_date} predates incident date {claim.incident_date}",
                    details={
                        "document_id": document.id,
                        "file_name": document.file_name,
                        "invoice_date": invoice_date,
                        "incident_date": claim.incident_date,
                    },
                )
        return GuardrailResult(
            code="INVOICE_DATE_BEFORE_INCIDENT",
            category=GuardrailCategory.FRAUD_RISK,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="No invoice date anomaly detected",
        )

    def check_repeat_claims(self, claim: Claim) -> GuardrailResult:
        prior_claims = self.claim_repository.get_claims_for_customer_last_12_months(
            customer_id=claim.customer_id,
            incident_date=claim.incident_date,
            exclude_claim_id=claim.id,
        )
        prior_claim_count = len(prior_claims)
        if prior_claim_count >= GuardrailConfig.REPEAT_CLAIMS_THRESHOLD:
            return GuardrailResult(
                code="REPEAT_CLAIMS_REVIEW_REQUIRED",
                category=GuardrailCategory.FRAUD_RISK,
                decision=GuardrailDecision.REVIEW_REQUIRED,
                severity=GuardrailSeverity.HIGH,
                message=f"Customer has {prior_claim_count} claims in the last 12 months",
                details={
                    "customer_id": claim.customer_id,
                    "prior_claim_count": prior_claim_count,
                    "months": GuardrailConfig.REPEAT_CLAIMS_MONTHS,
                    "threshold": GuardrailConfig.REPEAT_CLAIMS_THRESHOLD,
                    "prior_claim_ids": [prior_claim.id for prior_claim in prior_claims],
                },
            )
        return GuardrailResult(
            code="REPEAT_CLAIMS_REVIEW_REQUIRED",
            category=GuardrailCategory.FRAUD_RISK,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Repeat claim threshold not met",
        )

    def check_prior_rejected_claim(self, claim: Claim) -> GuardrailResult:
        if not claim.previous_claim_id:
            return GuardrailResult(
                code="PRIOR_REJECTED_CLAIM",
                category=GuardrailCategory.CLAIM,
                decision=GuardrailDecision.PASS,
                severity=GuardrailSeverity.LOW,
                message="No prior rejected claim linked",
            )
        previous_claim = self.claim_repository.get(claim.previous_claim_id)
        if previous_claim.status == ClaimStatus.REJECTED:
            return GuardrailResult(
                code="PRIOR_REJECTED_CLAIM",
                category=GuardrailCategory.CLAIM,
                decision=GuardrailDecision.REVIEW_REQUIRED,
                severity=GuardrailSeverity.HIGH,
                message="Claim is linked to a previously rejected claim and requires human review",
                details={
                    "current_claim_id": claim.id,
                    "previous_claim_id": previous_claim.id,
                    "previous_claim_status": previous_claim.status.value,
                },
            )
        return GuardrailResult(
            code="PRIOR_REJECTED_CLAIM",
            category=GuardrailCategory.CLAIM,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Linked previous claim was not rejected",
        )

    def check_payout_near_policy_limit(self, policy: Policy, payout_amount: Decimal) -> GuardrailResult:
        coverage_limit = Decimal(str(policy.coverage_limit))
        ratio = payout_amount / coverage_limit
        threshold_ratio = GuardrailConfig.PAYOUT_NEAR_THRESHOLD_PERCENTAGE
        if ratio >= threshold_ratio:
            return GuardrailResult(
                code="PAYOUT_NEAR_POLICY_LIMIT",
                category=GuardrailCategory.PAYMENT,
                decision=GuardrailDecision.REVIEW_REQUIRED,
                severity=GuardrailSeverity.HIGH,
                message="Payout amount is near policy coverage limit",
                details={
                    "payout_amount": str(payout_amount),
                    "coverage_limit": str(coverage_limit),
                    "ratio": str(ratio),
                    "threshold_ratio": str(threshold_ratio),
                },
            )
        return GuardrailResult(
            code="PAYOUT_NEAR_POLICY_LIMIT",
            category=GuardrailCategory.PAYMENT,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Payout amount is not near policy coverage limit",
        )

    def check_final_payout_not_above_approved_amount(
        self,
        approved_amount: Decimal,
        final_payout_amount: Decimal,
    ) -> GuardrailResult:
        if final_payout_amount > approved_amount:
            return GuardrailResult(
                code="FINAL_PAYOUT_EXCEEDS_APPROVED_AMOUNT",
                category=GuardrailCategory.PAYMENT,
                decision=GuardrailDecision.BLOCK,
                severity=GuardrailSeverity.CRITICAL,
                message="Final payout amount exceeds approved amount",
                details={
                    "approved_amount": str(approved_amount),
                    "final_payout_amount": str(final_payout_amount),
                },
            )
        return GuardrailResult(
            code="FINAL_PAYOUT_EXCEEDS_APPROVED_AMOUNT",
            category=GuardrailCategory.PAYMENT,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="Final payout amount does not exceed approved amount",
        )

    def check_high_risk_payment_has_human_approval(
        self,
        is_high_risk: bool,
        human_approval_present: bool,
    ) -> GuardrailResult:
        if is_high_risk and not human_approval_present:
            return GuardrailResult(
                code="HIGH_RISK_PAYMENT_REQUIRES_HUMAN_APPROVAL",
                category=GuardrailCategory.PAYMENT,
                decision=GuardrailDecision.BLOCK,
                severity=GuardrailSeverity.CRITICAL,
                message="Payment instruction cannot be created for high-risk claim without human approval",
                details={
                    "is_high_risk": is_high_risk,
                    "human_approval_present": human_approval_present,
                },
            )
        return GuardrailResult(
            code="HIGH_RISK_PAYMENT_REQUIRES_HUMAN_APPROVAL",
            category=GuardrailCategory.PAYMENT,
            decision=GuardrailDecision.PASS,
            severity=GuardrailSeverity.LOW,
            message="High-risk payment approval requirement satisfied",
        )

    def _summarise(self, results: list[GuardrailResult]) -> GuardrailEvaluationSummary:
        if any(result.decision == GuardrailDecision.BLOCK for result in results):
            decision = GuardrailDecision.BLOCK
        elif any(result.decision == GuardrailDecision.REVIEW_REQUIRED for result in results):
            decision = GuardrailDecision.REVIEW_REQUIRED
        else:
            decision = GuardrailDecision.PASS
        return GuardrailEvaluationSummary(overall_decision=decision, results=results)
