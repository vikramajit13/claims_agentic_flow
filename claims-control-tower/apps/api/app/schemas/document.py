from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentClassificationResult(BaseModel):
    document_type: str
    confidence: float = Field(ge=0, le=1)
    reason: str | None = None


class DocumentExtractedFields(BaseModel):
    invoice_number: str | None = None
    invoice_amount: float | None = None
    invoice_date: str | None = None
    vendor_name: str | None = None
    policy_number: str | None = None
    claim_reference: str | None = None
    currency: str | None = None
    repairer_name: str | None = None
    document_date: str | None = None


class DocumentQualityAssessment(BaseModel):
    quality_level: str
    overall_confidence: float = Field(ge=0, le=1)
    review_recommended: bool
    notes: list[str] = Field(default_factory=list)
    processing_mode: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None


class NormalizedDocumentRecord(BaseModel):
    document_id: int
    claim_id: int | None = None
    file_name: str
    content_type: str | None = None
    s3_uri: str
    document_type: str
    upload_status: str
    ocr_status: str
    raw_text: str | None = None
    normalized_text: str | None = None
    validation_results: dict | None = None
    document_classification: DocumentClassificationResult | dict | None = None
    extracted_fields: DocumentExtractedFields | dict | None = None
    quality_assessment: DocumentQualityAssessment | dict | None = None
    textract_blocks: list[dict] = Field(default_factory=list)
    confidence_score: float | None = None
    normalized_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class ClaimDocumentState(BaseModel):
    document_id: int
    document_type: str
    document_url: str
    uploaded_at: str
    status: str
    document_text: str | None = None
    ocr_status: str | None = None
    ocr_error: str | None = None
    validation_results: dict | None = None
    document_classification: dict | None = None
    extracted_fields: dict | None = None
    quality_assessment: dict | None = None
    normalized_payload: dict | None = None
    normalized_document_type: str | None = None
    normalized_confidence: float | None = None
    normalized_at: str | None = None
