from app.models.claim import ClaimStatus
from app.repositories.claim_repository import ClaimRepository


class ClaimsSystemAdapter:
    def __init__(self, claim_repo: ClaimRepository | None = None) -> None:
        self.claim_repo = claim_repo or ClaimRepository()

    def update_claim_status(self, claim_id: int, status: ClaimStatus):
        return self.claim_repo.update_status(claim_id, status)

    def get_claim_history(self, customer_id: int):
        return self.claim_repo.get_customer_claims(customer_id)

    def get_claims_for_customer_last_12_months(self, customer_id: int, incident_date: str, exclude_claim_id: int | None = None):
        return self.claim_repo.get_claims_for_customer_last_12_months(customer_id, incident_date, exclude_claim_id)
