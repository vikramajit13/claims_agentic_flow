from __future__ import annotations

from datetime import date

from app.models.claim import Claim
from app.models.policy import Policy
from app.repositories.policy_repository import PolicyRepository
from app.schemas.workflow_schema import CoverageValidationResult


class PolicyAdminAdapter:
    def __init__(self, policy_repo: PolicyRepository | None = None) -> None:
        self.policy_repo = policy_repo or PolicyRepository()

    def get_policy(self, policy_id: int) -> Policy:
        return self.policy_repo.get(policy_id)

    def validate_coverage(self, claim: Claim) -> CoverageValidationResult:
        policy = self.get_policy(claim.policy_id)
        reasons: list[str] = []

        if policy.customer_id != claim.customer_id:
            reasons.append("Policy customer does not match claim customer")
        if policy.status.lower() != "active":
            reasons.append("Policy is not active")
        if claim.claim_type.lower() not in [claim_type.lower() for claim_type in policy.covered_claim_types]:
            reasons.append("Claim type is not covered by this policy")

        incident_date = date.fromisoformat(claim.incident_date)
        active_from = date.fromisoformat(policy.active_from)
        active_to = date.fromisoformat(policy.active_to)
        if incident_date < active_from or incident_date > active_to:
            reasons.append("Incident date falls outside policy coverage period")

        return CoverageValidationResult(
            is_valid=not reasons,
            reasons=reasons,
            policy_id=policy.id,
            coverage_limit=policy.coverage_limit,
        )
