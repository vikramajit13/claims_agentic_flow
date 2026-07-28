import asyncio

from app.graph.state import ClaimGraphState
from app.nodes.analyse_risk import analyse_risk
from app.schemas.document import ClaimDocumentState


def test_analyse_risk_flags_invoice_and_quality_issues():
    state = ClaimGraphState(
        claim_id=1,
        claim_type="motor",
        incident_date="2026-07-10",
        claim_description="Accident damage",
        claim_amount=2400,
        claim_documents=[
            ClaimDocumentState(
                document_id=1,
                document_type="invoice",
                document_url="s3://bucket/invoice.pdf",
                uploaded_at="2026-07-10T10:00:00+10:00",
                status="ocr_completed",
                document_text="Repair invoice",
                ocr_status="completed",
                normalized_document_type="invoice",
                normalized_confidence=0.62,
                normalized_payload={
                    "document_type": "invoice",
                    "extracted_fields": {
                        "invoice_amount": 2400,
                        "invoice_date": "2026-07-12",
                        "vendor_name": "Sydney Repairs",
                        "currency": "AUD",
                    },
                },
                extracted_fields={
                    "invoice_amount": 2400,
                    "invoice_date": "2026-07-12",
                    "vendor_name": "Sydney Repairs",
                    "currency": "AUD",
                },
                quality_assessment={
                    "review_recommended": True,
                },
            ),
        ],
    )

    result = asyncio.run(analyse_risk(state))

    assert result["current_step"] == "risk_analysis"
    assert result["requires_human_review"] is True
    assert result["risk_level"] == "HIGH"
    assert "invoice_after_incident:1" in result["errors"]
    assert "low_confidence_document:1" in result["errors"]
    assert "low_quality_document:1" in result["errors"]
    assert any("Invoice date 2026-07-12 is after incident date 2026-07-10" in factor for factor in result["risk_factors"])

def test_analyse_risk_flags_missing_invoice():
    state = ClaimGraphState(
        claim_id=2,
        claim_type="motor",
        incident_date="2026-07-10",
        claim_description="Accident damage",
        claim_amount=2400,
        claim_documents=[
            ClaimDocumentState(
                document_id=2,
                document_type="invoice",
                document_url="s3://bucket/invoice.pdf",
                uploaded_at="2026-07-10T10:00:00+10:00",
                status="ocr_completed",
                document_text="Repair invoice",
                ocr_status="completed",
                normalized_document_type="invoice",
                normalized_confidence=0.85,
                normalized_payload={
                    "document_type": "invoice",
                    "extracted_fields": {
                        "invoice_amount": 2400,
                        "invoice_date": "2026-07-12",
                        "vendor_name": "Sydney Repairs",
                        "currency": "AUD",
                    },
                },
                extracted_fields={
                    "invoice_amount": 2400,
                    "invoice_date": "2026-07-12",
                    "vendor_name": "Sydney Repairs",
                    "currency": "AUD",
                },
                quality_assessment={
                    "review_recommended": True,
                },
            ),
        ],
    )

    result = asyncio.run(analyse_risk(state))

    assert result["current_step"] == "risk_analysis"
    assert result["requires_human_review"] is True
    assert result["risk_level"] == "HIGH"
    assert "invoice_after_incident:1" in result["errors"]
    assert "low_confidence_document:1" in result["errors"]
    assert "low_quality_document:1" in result["errors"]
    assert any("Invoice date 2026-07-12 is after incident date 2026-07-10" in factor for factor in result["risk_factors"])

def test_ocr_failed_document_flags_risk():
    state = ClaimGraphState(
        claim_id=2,
        claim_type="motor",
        incident_date="2026-07-10",
        claim_description="Accident damage",
        claim_amount=2400,
        claim_documents=[
            ClaimDocumentState(
                document_id=2,
                document_type="invoice",
                document_url="s3://bucket/invoice.pdf",
                uploaded_at="2026-07-10T10:00:00+10:00",
                status="failed",
                document_text="Repair invoice",
                ocr_status="failed",
                normalized_document_type="invoice",
                normalized_confidence=0.85,
                normalized_payload={
                    "document_type": "invoice",
                    "extracted_fields": {
                        "invoice_amount": 2400,
                        "invoice_date": "2026-07-12",
                        "vendor_name": "Sydney Repairs",
                        "currency": "AUD",
                    },
                },
                extracted_fields={
                    "invoice_amount": 2400,
                    "invoice_date": "2026-07-12",
                    "vendor_name": "Sydney Repairs",
                    "currency": "AUD",
                },
                quality_assessment={
                    "review_recommended": True,
                },
            ),
        ],
    )

    result = asyncio.run(analyse_risk(state))

    assert result["current_step"] == "risk_analysis"
    assert result["requires_human_review"] is True
    assert result["risk_level"] == "HIGH"
    assert "OCR failed for document 2" in result["errors"]
    
    

