from __future__ import annotations

from pydantic import BaseModel, Field

from app.enums import ClaimStatus, DocumentStatus, OcrStatus, WorkflowStatus, WorkflowStep


class ClaimCreateRequest(BaseModel):
    claim_number: str
    customer_id: int
    claim_type: str
    description: str | None = None
    incident_date: str | None = None
    claim_amount: float | None = Field(default=None, ge=0)


class DocumentPresignRequest(BaseModel):
    file_name: str
    content_type: str | None = None
    run_ocr: bool = True


class DocumentUploadCompleteRequest(BaseModel):
    trigger_ocr: bool | None = None


class DocumentPresignResponse(BaseModel):
    document_id: int
    upload_url: str
    upload_method: str = "PUT"
    upload_headers: dict[str, str] = Field(default_factory=dict)
    s3_uri: str
    s3_bucket: str
    s3_key: str
    expires_in_seconds: int


class ClaimDocumentResponse(BaseModel):
    id: int
    file_name: str
    content_type: str | None = None
    s3_uri: str
    s3_bucket: str
    s3_key: str
    upload_status: DocumentStatus
    ocr_requested: bool
    ocr_status: OcrStatus
    ocr_job_id: str | None = None
    ocr_error: str | None = None
    ocr_text: str | None = None
    normalized_text: str | None = None
    validation_results: dict | None = None
    document_classification: dict | None = None
    extracted_fields: dict | None = None
    quality_assessment: dict | None = None
    normalized_payload: dict | None = None
    normalized_document_type: str | None = None
    normalized_confidence: float | None = None
    normalized_at: str | None = None
    created_at: str
    updated_at: str


class ClaimResponse(BaseModel):
    id: int
    claim_number: str
    customer_id: int
    claim_type: str
    description: str | None = None
    incident_date: str | None = None
    claim_amount: float | None = None
    status: ClaimStatus
    documents: list[ClaimDocumentResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class WorkflowStartRequest(BaseModel):
    hitl_required: bool | None = None
    notes: list[str] = Field(default_factory=list)


class WorkflowRunResponse(BaseModel):
    id: int
    claim_id: int
    status: WorkflowStatus
    current_step: WorkflowStep
    hitl_required: bool
    next_action: str
    notes: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class InternalS3ObjectCreatedRequest(BaseModel):
    document_id: int
    claim_id: int
    s3_bucket: str
    s3_key: str
    queued_for_ocr: bool = False
    ocr_job_id: str | None = None


class InternalProcessOcrRequest(BaseModel):
    document_id: int
