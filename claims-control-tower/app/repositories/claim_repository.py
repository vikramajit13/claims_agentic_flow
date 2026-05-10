from __future__ import annotations

from datetime import date, datetime, timedelta

from app.database import get_store
from app.models.claim import Claim, ClaimStatus


class ClaimRepository:
    def __init__(self) -> None:
        self.store = get_store()

    def create(self, claim: Claim) -> Claim:
        self.store.claims[claim.id] = claim
        return claim

    def get(self, claim_id: int) -> Claim:
        return self.store.claims[claim_id]

    def list(self) -> list[Claim]:
        return list(self.store.claims.values())

    def update(self, claim: Claim) -> Claim:
        self.store.claims[claim.id] = claim
        return claim

    def update_status(self, claim_id: int, status: ClaimStatus) -> Claim:
        claim = self.get(claim_id)
        updated = claim.copy(update={"status": status, "updated_at": _now_iso()})
        return self.update(updated)

    def get_customer_claims(self, customer_id: int) -> list[Claim]:
        return [claim for claim in self.store.claims.values() if claim.customer_id == customer_id]

    def get_recent_customer_claims(self, customer_id: int, days: int, exclude_claim_id: int | None = None) -> list[Claim]:
        threshold = datetime.utcnow() - timedelta(days=days)
        recent_claims: list[Claim] = []
        for claim in self.get_customer_claims(customer_id):
            if exclude_claim_id is not None and claim.id == exclude_claim_id:
                continue
            created_at = datetime.fromisoformat(claim.created_at)
            if created_at >= threshold:
                recent_claims.append(claim)
        return recent_claims

    def get_claims_for_customer_last_12_months(
        self,
        customer_id: int,
        incident_date: str,
        exclude_claim_id: int | None = None,
    ) -> list[Claim]:
        reference_date = date.fromisoformat(incident_date)
        threshold = reference_date - timedelta(days=365)
        claims: list[Claim] = []
        for claim in self.get_customer_claims(customer_id):
            if exclude_claim_id is not None and claim.id == exclude_claim_id:
                continue
            claim_incident_date = date.fromisoformat(claim.incident_date)
            if threshold <= claim_incident_date <= reference_date:
                claims.append(claim)
        return claims


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
