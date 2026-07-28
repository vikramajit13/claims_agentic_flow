import asyncio

from app.graph.state import ClaimGraphState
from app.nodes.validate_claim_context import validate_claim_context
from app.schemas.document import ClaimDocumentState


def test_validate_claim_context_accepts_normalized_motor_documents():
    state = ClaimGraphState(
        claim_id=1,
        claim_type="motor",
        incident_date="2026-07-10",
        claim_description="Accident damage",
        claim_amount=2400,
        claim_documents=[
            ClaimDocumentState(
                document_id=1,
                document_type="photo",
                document_url="s3://bucket/photo.jpg",
                uploaded_at="2026-07-10T10:00:00+10:00",
                status="ocr_completed",
                document_text="Photo of front bumper damage",
                ocr_status="completed",
                normalized_document_type="photo",
                normalized_confidence=0.95,
                normalized_payload={
                    "document_type": "photo",
                    "extracted_fields": {},
                },
                quality_assessment={
                    "review_recommended": False,
                },
            ),
            ClaimDocumentState(
                document_id=2,
                document_type="repair_estimate",
                document_url="s3://bucket/estimate.pdf",
                uploaded_at="2026-07-10T10:10:00+10:00",
                status="ocr_completed",
                document_text="Estimate total 2400",
                ocr_status="completed",
                normalized_document_type="repair_estimate",
                normalized_confidence=0.92,
                normalized_payload={
                    "document_type": "repair_estimate",
                    "extracted_fields": {
                        "invoice_amount": 2400,
                        "invoice_date": "2026-07-10",
                        "vendor_name": "Sydney Repairs",
                        "currency": "AUD",
                    },
                },
                extracted_fields={
                    "invoice_amount": 2400,
                    "invoice_date": "2026-07-10",
                    "vendor_name": "Sydney Repairs",
                    "currency": "AUD",
                },
                quality_assessment={
                    "review_recommended": False,
                },
            ),
        ],
    )

    result = asyncio.run(validate_claim_context(state))

    assert result["current_step"] == "context_validated"
    assert result["requires_human_review"] is False
    assert result["required_documents"] == ["photo", "repair_estimate"]


def test_validate_claim_context_flags_missing_required_docs():
    state = ClaimGraphState(
        claim_id=1,
        claim_type="travel",
        claim_description="Trip interruption",
        claim_amount=1200,
        claim_documents=[],
    )

    result = asyncio.run(validate_claim_context(state))

    assert result["requires_human_review"] is True
    assert "missing_claim_documents" in result["errors"]
    
def test_validate_claim_context_flags_missing_claim_description():
    state = ClaimGraphState(
        claim_id=1,
        claim_type="travel",
        claim_description=None,
        claim_amount=1200,
        claim_documents=[],
    )

    result = asyncio.run(validate_claim_context(state))

    assert result["requires_human_review"] is True
    assert "missing_claim_description" in result["errors"]
    
def test_validate_claim_context_flags_missing_claim_amount():
    state = ClaimGraphState(
        claim_id=1,
        claim_type="travel",
        claim_description="Trip interruption",
        claim_amount=None,
        claim_documents=[],
    )

    result = asyncio.run(validate_claim_context(state))

    assert result["requires_human_review"] is True
    assert "missing_claim_amount" in result["errors"]   
