from __future__ import annotations

from app.database import get_store
from app.models.claim_document import ClaimDocument, DocumentVerificationStatus, DocumentType


class DocumentAdapter:
    REQUIRED_DOCUMENTS: dict[str, list[DocumentType]] = {
        "motor": [DocumentType.PHOTO, DocumentType.REPAIR_ESTIMATE],
        "theft": [DocumentType.POLICE_REPORT],
        "medical": [DocumentType.MEDICAL_REPORT, DocumentType.INVOICE],
        "travel": [DocumentType.INVOICE],
    }

    def __init__(self) -> None:
        self.store = get_store()

    def get_required_documents(self, claim_type: str) -> list[DocumentType]:
        return self.REQUIRED_DOCUMENTS.get(claim_type.lower(), [])

    def validate_documents(self, claim_id: int, claim_type: str) -> dict:
        documents = self.get_documents_for_claim(claim_id)
        provided_documents = [document.document_type.value for document in documents]
        required_documents = [document_type.value for document_type in self.get_required_documents(claim_type)]
        missing_documents = [document for document in required_documents if document not in provided_documents]

        reasons = [f"Missing {document.replace('_', ' ')}" for document in missing_documents]
        return {
            "documents": documents,
            "required_documents": required_documents,
            "provided_documents": provided_documents,
            "missing_documents": missing_documents,
            "reasons": reasons,
        }

    def get_documents_for_claim(self, claim_id: int) -> list[ClaimDocument]:
        return [document for document in self.store.documents.values() if document.claim_id == claim_id]

    def update_document_status(self, document_id: int, status: DocumentVerificationStatus) -> ClaimDocument:
        document = self.store.documents[document_id]
        updated = document.copy(update={"verification_status": status})
        self.store.documents[document_id] = updated
        return updated
