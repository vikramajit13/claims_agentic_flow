from app.enums import DocumentStatus, OcrStatus
from app.mappers.document_mapper import map_claim_document_response, map_claim_documents_response
from app.schemas.schemas import ClaimDocumentResponse


def test_map_claim_document_response_uses_graph_state_shape():
    document = ClaimDocumentResponse(
        id=12,
        file_name="repair-invoice.pdf",
        content_type="application/pdf",
        s3_uri="s3://claims-bucket/claims/12/repair-invoice.pdf",
        s3_bucket="claims-bucket",
        s3_key="claims/12/repair-invoice.pdf",
        upload_status=DocumentStatus.OCR_COMPLETED,
        ocr_requested=True,
        ocr_status=OcrStatus.COMPLETED,
        ocr_job_id="job-123",
        ocr_error=None,
        ocr_text="Invoice text",
        normalized_text="normalized invoice text",
        validation_results={"passed": True},
        document_classification={"document_type": "INVOICE"},
        extracted_fields={"invoice_amount": 4200},
        quality_assessment={"quality": "good"},
        normalized_payload={
            "document_id": 12,
            "claim_id": 44,
            "file_name": "repair-invoice.pdf",
            "document_type": "INVOICE",
        },
        normalized_document_type="INVOICE",
        normalized_confidence=0.96,
        normalized_at="2026-07-16T10:06:00+10:00",
        created_at="2026-07-16T10:00:00+10:00",
        updated_at="2026-07-16T10:05:00+10:00",
    )

    mapped = map_claim_document_response(document)

    assert mapped.document_id == 12
    assert mapped.document_type == "INVOICE"
    assert mapped.document_url == "s3://claims-bucket/claims/12/repair-invoice.pdf"
    assert mapped.uploaded_at == "2026-07-16T10:00:00+10:00"
    assert mapped.status == "ocr_completed"
    assert mapped.document_text == "normalized invoice text"
    assert mapped.ocr_status == "completed"
    assert mapped.ocr_error is None
    assert mapped.normalized_payload["document_type"] == "INVOICE"
    assert mapped.normalized_document_type == "INVOICE"
    assert mapped.normalized_confidence == 0.96


def test_map_claim_documents_response_handles_empty_lists():
    assert map_claim_documents_response([]) == []
