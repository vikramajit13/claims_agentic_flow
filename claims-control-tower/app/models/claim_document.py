
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class DocumentType(str, Enum):
    INVOICE = "invoice"
    PHOTO = "photo"
    POLICE_REPORT = "police_report"
    REPAIR_ESTIMATE = "repair_estimate"
    MEDICAL_REPORT = "medical_report"
    
class DocumentVerificationStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"

class ClaimDocument(BaseModel):
    id: Optional[int] = Field(None, description="Unique identifier for the claim document")
    claim_id: int = Field(..., description="ID of the claim associated with this document")
    document_type: DocumentType = Field(..., description="Type of the document (e.g., 'photo', 'report', 'invoice')")
    file_name: str = Field(..., description="Name of the file")
    storage_url: str = Field(..., description="URL where the document is stored")
    verification_status: DocumentVerificationStatus = Field(..., description="Verification status of the document (e.g., 'pending', 'approved', 'rejected')")
    created_at: Optional[str] = Field(None, description="Timestamp when the document was created")
