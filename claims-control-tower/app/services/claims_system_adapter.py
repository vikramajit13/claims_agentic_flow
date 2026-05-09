from app.models.claim import ClaimStatus
from app.repositories.claim_repository import ClaimRepository


class ClaimsSystemAdapter:
    def __init__(self, claim_repo: ClaimRepository | None = None) -> None:
        self.claim_repo = claim_repo or ClaimRepository()

    def update_claim_status(self, claim_id: int, status: ClaimStatus):
        return self.claim_repo.update_status(claim_id, status)

    def get_claim_history(self, customer_id: int):
        return self.claim_repo.get_customer_claims(customer_id)
