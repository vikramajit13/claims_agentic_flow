from app.config import settings
from app.enums import RecommendationDecision
from app.models.claim import Claim
from app.schemas.workflow_schema import (
    AdjudicationRecommendation,
    CoverageValidationResult,
    DocumentValidationResult,
    FraudRiskResult,
)


class AdjudicationService:
    def reject(self, claim: Claim, reasons: list[str]) -> AdjudicationRecommendation:
        return AdjudicationRecommendation(
            recommendation=RecommendationDecision.REJECT,
            reason="; ".join(reasons),
            recommended_amount=0.0,
            requires_human_review=False,
        )

    def recommend(
        self,
        claim: Claim,
        coverage_result: CoverageValidationResult,
        evidence_result: DocumentValidationResult,
        risk_result: FraudRiskResult,
    ) -> AdjudicationRecommendation:
        if not coverage_result.is_valid:
            return self.reject(claim, coverage_result.reasons)

        if not evidence_result.is_valid:
            return AdjudicationRecommendation(
                recommendation=RecommendationDecision.REQUEST_MORE_INFO,
                reason="Missing required evidence",
                recommended_amount=0.0,
                requires_human_review=False,
            )

        if risk_result.risk_level.value == "HIGH":
            return AdjudicationRecommendation(
                recommendation=RecommendationDecision.REFER_TO_HUMAN,
                reason="High fraud risk score",
                recommended_amount=claim.claim_amount,
                requires_human_review=True,
            )

        if claim.claim_amount > settings.payment_approval_threshold:
            return AdjudicationRecommendation(
                recommendation=RecommendationDecision.REFER_TO_HUMAN,
                reason="Claim amount exceeds payment approval threshold",
                recommended_amount=claim.claim_amount,
                requires_human_review=True,
            )

        return AdjudicationRecommendation(
            recommendation=RecommendationDecision.APPROVE,
            reason="Claim passed automated checks",
            recommended_amount=claim.claim_amount,
            requires_human_review=False,
        )
