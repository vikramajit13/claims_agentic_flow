from app.document_intelligence_service import (
    DocumentIntelligenceOrchestrator,
    FallbackDocumentIntelligenceService,
    LLMDocumentIntelligenceService,
    TextractLine,
    TextractResult,
)


class FakeLLMService(LLMDocumentIntelligenceService):
    def is_enabled(self) -> bool:
        return True

    def process(self, *, file_name: str, normalized_text: str, textract_result: TextractResult) -> dict:
        return {
            "document_classification": {
                "document_type": "invoice",
                "confidence": 0.96,
                "reason": "LLM identified invoice structure and payment fields.",
            },
            "extracted_fields": {
                "document_type": "invoice",
                "fields": {
                    "invoice_number": "LLM-7788",
                    "invoice_amount": 6400.0,
                    "invoice_date": "2026-07-05",
                    "vendor_name": "Sydney Smash Repairs",
                    "policy_number": "POL-7788",
                    "claim_reference": "CLM-7788",
                },
                "field_count": 6,
            },
            "quality_assessment": {
                "quality_level": "high",
                "overall_confidence": 0.91,
                "review_recommended": False,
                "notes": ["Structured invoice fields are present."],
                "processing_mode": "llm",
                "fallback_used": False,
            },
        }


def test_document_intelligence_prefers_llm_when_available():
    textract_result = TextractResult(
        raw_text="Invoice Number: INV-1001 Amount Due: 4200.00 Vendor: ABC Repairs",
        lines=[
            TextractLine(text="Invoice Number: INV-1001", confidence=98.0),
            TextractLine(text="Amount Due: 4200.00", confidence=97.0),
        ],
        blocks=[
            {"block_type": "LINE", "text": "Invoice Number: INV-1001", "confidence": 98.0},
            {"block_type": "LINE", "text": "Amount Due: 4200.00", "confidence": 97.0},
        ],
    )
    orchestrator = DocumentIntelligenceOrchestrator(
        llm_service=FakeLLMService(),
        fallback_service=FallbackDocumentIntelligenceService(),
    )

    result = orchestrator.process(file_name="repair-invoice.pdf", textract_result=textract_result)

    assert result.document_classification["document_type"] == "invoice"
    assert result.extracted_fields["fields"]["invoice_number"] == "LLM-7788"
    assert result.quality_assessment["processing_mode"] == "llm"
    assert result.quality_assessment["fallback_used"] is False


def test_document_intelligence_builds_normalized_record():
    textract_result = TextractResult(
        raw_text="Invoice Number: INV-1001 Amount Due: 4200.00 Vendor: ABC Repairs",
        lines=[TextractLine(text="Invoice Number: INV-1001", confidence=98.0)],
        blocks=[{"block_type": "LINE", "text": "Invoice Number: INV-1001", "confidence": 98.0}],
    )
    orchestrator = DocumentIntelligenceOrchestrator(
        llm_service=FakeLLMService(),
        fallback_service=FallbackDocumentIntelligenceService(),
    )

    intelligence_result = orchestrator.process(file_name="repair-invoice.pdf", textract_result=textract_result)
    normalized = orchestrator.build_normalized_record(
        document_id=1,
        claim_id=10,
        file_name="repair-invoice.pdf",
        content_type="application/pdf",
        s3_uri="s3://bucket/claims/10/repair-invoice.pdf",
        s3_bucket="bucket",
        s3_key="claims/10/repair-invoice.pdf",
        upload_status="ocr_completed",
        ocr_status="completed",
        intelligence_result=intelligence_result,
    )

    assert normalized.document_type == "invoice"
    assert normalized.extracted_fields.invoice_amount == 6400.0
    assert normalized.quality_assessment.quality_level == "high"
