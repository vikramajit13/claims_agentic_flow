from __future__ import annotations

from app.models.claim import Claim
from app.models.claim_document import DocumentVerificationStatus, DocumentType
from app.schemas.workflow_schema import DocumentValidationResult
from app.services.document_adapter import DocumentAdapter


class DocumentValidationService:
    def __init__(self, document_adapter: DocumentAdapter | None = None) -> None:
        self.document_adapter = document_adapter or DocumentAdapter()

    def validate_documents(self, claim: Claim) -> DocumentValidationResult:
        result = self.document_adapter.validate_documents(claim.id, claim.claim_type)

        for document in result["documents"]:
            self.document_adapter.update_document_status(
                document.id,
                DocumentVerificationStatus.VALID if document.document_type.value in result["provided_documents"] else DocumentVerificationStatus.MISSING,
            )

        return DocumentValidationResult(
            is_valid=not result["missing_documents"],
            required_documents=result["required_documents"],
            provided_documents=result["provided_documents"],
            missing_documents=result["missing_documents"],
            reasons=result["reasons"],
        )

    def get_required_documents(self, claim_type: str) -> list[DocumentType]:
        return self.document_adapter.get_required_documents(claim_type)
