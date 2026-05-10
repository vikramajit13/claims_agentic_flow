from datetime import date

from app.models.claim import Claim
from app.models.claim_document import ClaimDocument, DocumentType
from app.schemas.workflow_schema import RiskSignalResult


class RiskSignalService:
    def evaluate(self, claim: Claim, documents: list[ClaimDocument], prior_12_month_claim_count: int) -> RiskSignalResult:
        risk_factors: list[str] = []

        for document in documents:
            if document.document_type != DocumentType.INVOICE:
                continue
            invoice_date = document.document_metadata.get("invoice_date")
            if invoice_date and date.fromisoformat(invoice_date) < date.fromisoformat(claim.incident_date):
                risk_factors.append(
                    f"Invoice date {invoice_date} predates incident date {claim.incident_date}"
                )

        if prior_12_month_claim_count >= 3:
            risk_factors.append(f"Customer has {prior_12_month_claim_count} claims in the last 12 months")

        if not risk_factors:
            return RiskSignalResult(
                requires_human_review=False,
                reason="No additional payment risk signals detected",
                risk_factors=[],
            )

        return RiskSignalResult(
            requires_human_review=True,
            reason="Auto-payment blocked due to invoice anomaly and high claim frequency",
            risk_factors=risk_factors,
            recommended_action="ADJUSTER_REVIEW_REQUIRED",
        )
