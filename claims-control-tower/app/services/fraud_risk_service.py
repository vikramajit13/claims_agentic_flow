from __future__ import annotations

from datetime import date

from app.config import settings
from app.enums import FraudRiskLevel
from app.models.claim import Claim
from app.models.policy import Policy
from app.schemas.workflow_schema import DocumentValidationResult, FraudRiskResult


class FraudRiskService:
    def evaluate(
        self,
        claim: Claim,
        policy: Policy,
        evidence_result: DocumentValidationResult,
        prior_claim_count_30_days: int,
    ) -> FraudRiskResult:
        score = 0
        factors: list[str] = []

        if claim.claim_amount > policy.coverage_limit * 0.8:
            score += 30
            factors.append("Claim amount is greater than 80% of coverage limit")

        if prior_claim_count_30_days > 0:
            score += 20
            factors.append("Multiple claims by same customer in the last 30 days")

        incident_gap = (date.fromisoformat(claim.incident_date) - date.fromisoformat(policy.active_from)).days
        if incident_gap <= 7:
            score += 25
            factors.append("Incident occurred within 7 days of policy start")

        if evidence_result.missing_documents:
            score += min(20, 10 * len(evidence_result.missing_documents))
            factors.append(f"Missing critical evidence: {', '.join(evidence_result.missing_documents)}")

        description = claim.description.lower()
        suspicious_hits = [keyword for keyword in settings.suspicious_keywords if keyword in description]
        if suspicious_hits:
            score += 15
            factors.append(f"Claim description contains suspicious keywords: {', '.join(suspicious_hits)}")

        score = min(score, 100)

        if score >= 70:
            risk_level = FraudRiskLevel.HIGH
        elif score >= 40:
            risk_level = FraudRiskLevel.MEDIUM
        else:
            risk_level = FraudRiskLevel.LOW

        return FraudRiskResult(risk_score=score, risk_level=risk_level, risk_factors=factors)
