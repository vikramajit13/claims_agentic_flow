from typing import Optional

from pydantic import BaseModel, Field

from app.models.claim import Claim, ClaimStatus
from app.models.claim_document import ClaimDocument, DocumentType


class DocumentUpload(BaseModel):
    document_type: DocumentType
    file_name: str
    storage_url: str
    document_metadata: dict = Field(default_factory=dict)


class ClaimCreateRequest(BaseModel):
    claim_number: str
    customer_id: int
    policy_id: int
    claim_type: str
    claim_amount: float = Field(..., gt=0)
    incident_date: str
    description: str
    documents: list[DocumentUpload] = Field(default_factory=list)


class ClaimResponse(BaseModel):
    claim: Claim
    documents: list[ClaimDocument] = Field(default_factory=list)


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatus
    reason: Optional[str] = None
