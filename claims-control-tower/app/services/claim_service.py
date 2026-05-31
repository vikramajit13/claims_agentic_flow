from __future__ import annotations

from datetime import datetime

from app.database import get_store
from app.models.claim import Claim, ClaimStatus
from app.models.claim_document import ClaimDocument, DocumentVerificationStatus
from app.repositories.claim_repository import ClaimRepository
from app.schemas.claim_schema import ClaimCreateRequest, ClaimResponse


class ClaimService:
    def __init__(self, claim_repo: ClaimRepository | None = None) -> None:
        self.claim_repo = claim_repo or ClaimRepository()
        self.store = get_store()

    def submit_claim(self, claim_data: ClaimCreateRequest) -> ClaimResponse:
        now = _now_iso()
        claim = Claim(
            id=self.store.next_id("claims"),
            claim_number=claim_data.claim_number,
            customer_id=claim_data.customer_id,
            policy_id=claim_data.policy_id,
            claim_type=claim_data.claim_type.lower(),
            claim_amount=claim_data.claim_amount,
            incident_date=claim_data.incident_date,
            description=claim_data.description,
            previous_claim_id=claim_data.previous_claim_id,
            status=ClaimStatus.SUBMITTED,
            created_at=now,
            updated_at=now,
        )
        self.claim_repo.create(claim)

        documents: list[ClaimDocument] = []
        for document in claim_data.documents:
            claim_document = ClaimDocument(
                id=self.store.next_id("documents"),
                claim_id=claim.id,
                document_type=document.document_type,
                file_name=document.file_name,
                storage_url=document.storage_url,
                document_metadata=document.document_metadata,
                verification_status=DocumentVerificationStatus.PENDING,
                created_at=now,
            )
            self.store.documents[claim_document.id] = claim_document
            documents.append(claim_document)

        return ClaimResponse(claim=claim, documents=documents)

    def get_claim(self, claim_id: int) -> Claim:
        return self.claim_repo.get(claim_id)

    def list_claims(self) -> list[Claim]:
        return self.claim_repo.list()

    def update_status(
        self,
        claim_id: int,
        status: ClaimStatus,
        rejection_reason: str | None = None,
        approved_reason: str | None = None,
    ) -> Claim:
        return self.claim_repo.update_status(
            claim_id,
            status,
            rejection_reason=rejection_reason,
            approved_reason=approved_reason,
        )

    def get_claim_documents(self, claim_id: int) -> list[ClaimDocument]:
        return [document for document in self.store.documents.values() if document.claim_id == claim_id]

    def get_claim_response(self, claim_id: int) -> ClaimResponse:
        return ClaimResponse(claim=self.get_claim(claim_id), documents=self.get_claim_documents(claim_id))


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
