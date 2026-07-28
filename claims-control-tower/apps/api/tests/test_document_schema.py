from datetime import datetime, timezone

from app.schemas.document import (
    DocumentClassificationResult,
    DocumentExtractedFields,
    DocumentQualityAssessment,
    NormalizedDocumentRecord,
)


def test_normalized_document_record_supports_structured_evidence():
    record = NormalizedDocumentRecord(
        document_id=1,
        claim_id=10,
        file_name="repair-invoice.pdf",
        content_type="application/pdf",
        s3_uri="s3://bucket/claims/10/repair-invoice.pdf",
        document_type="INVOICE",
        upload_status="ocr_completed",
        ocr_status="completed",
        raw_text="Invoice total 4200",
        normalized_text="invoice total 4200 aud",
        validation_results={"has_text": True},
        document_classification=DocumentClassificationResult(
            document_type="INVOICE",
            confidence=0.97,
            reason="Invoice keywords detected",
        ),
        extracted_fields=DocumentExtractedFields(
            invoice_amount=4200,
            invoice_date="2026-07-16",
            vendor_name="ABC Repairs",
            currency="AUD",
        ),
        quality_assessment=DocumentQualityAssessment(
            quality_level="high",
            overall_confidence=0.96,
            review_recommended=False,
            notes=["Clear invoice scan"],
            processing_mode="llm",
        ),
        textract_blocks=[{"block_type": "LINE", "text": "Invoice total 4200"}],
        confidence_score=0.96,
        normalized_at=datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc),
        metadata={"source": "textract"},
    )

    assert record.document_classification.document_type == "INVOICE"
    assert record.extracted_fields.invoice_amount == 4200
    assert record.quality_assessment.quality_level == "high"
    assert record.metadata["source"] == "textract"
