import asyncio
from unittest.mock import AsyncMock, patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.enums import DocumentStatus, OcrStatus
from app.graph.builder import ClaimReviewGraphBuilder
from app.graph.state import ClaimGraphState
from app.schemas.schemas import ClaimDocumentResponse


def test_claim_graph_interrupts_and_resumes_through_human_review():
    graph = ClaimReviewGraphBuilder().build().compile(checkpointer=InMemorySaver())
    initial_state = ClaimGraphState(claim_id=501)
    thread_id = "claim-hitl-thread-501"

    mocked_claim = AsyncMock(
        description="Motor accident with repair invoice anomaly",
        claim_amount=2400,
        claim_type="motor",
        incident_date="2026-07-10",
        documents=[
            ClaimDocumentResponse(
                id=7,
                file_name="repair-invoice.pdf",
                content_type="application/pdf",
                s3_uri="s3://claims-bucket/claims/501/repair-invoice.pdf",
                s3_bucket="claims-bucket",
                s3_key="claims/501/repair-invoice.pdf",
                upload_status=DocumentStatus.OCR_COMPLETED,
                ocr_requested=True,
                ocr_status=OcrStatus.COMPLETED,
                ocr_job_id=None,
                ocr_error=None,
                ocr_text="Repair invoice for front bumper damage",
                normalized_text="Repair invoice for front bumper damage",
                validation_results=None,
                document_classification={"document_type": "invoice"},
                extracted_fields={
                    "invoice_amount": 2400,
                    "invoice_date": "2026-07-12",
                    "vendor_name": "Sydney Repairs",
                    "currency": "AUD",
                },
                quality_assessment={"review_recommended": True},
                normalized_payload={
                    "document_type": "invoice",
                    "extracted_fields": {
                        "invoice_amount": 2400,
                        "invoice_date": "2026-07-12",
                        "vendor_name": "Sydney Repairs",
                        "currency": "AUD",
                    },
                },
                normalized_document_type="invoice",
                normalized_confidence=0.62,
                normalized_at="2026-07-10T10:05:00+10:00",
                created_at="2026-07-10T10:00:00+10:00",
                updated_at="2026-07-10T10:05:00+10:00",
            )
        ],
    )

    with patch("app.claim_service.ClaimService.get_claim", new_callable=AsyncMock) as mock_get_claim:
        mock_get_claim.return_value = mocked_claim

        interrupted = asyncio.run(
            graph.ainvoke(initial_state, config={"configurable": {"thread_id": thread_id}})
        )

        assert "__interrupt__" in interrupted
        assert interrupted["__interrupt__"]

        interrupt_payload = getattr(interrupted["__interrupt__"][0], "value", interrupted["__interrupt__"][0])
        assert interrupt_payload["step"] == "human_review"
        assert interrupt_payload["claim_id"] == 501
        assert interrupt_payload["risk_level"] == "HIGH"
        assert interrupt_payload["risk_score"] >= 70

        resumed = asyncio.run(
            graph.ainvoke(
                Command(resume={"decision": "approve", "notes": "Manual review completed."}),
                config={"configurable": {"thread_id": thread_id}},
            )
        )

    assert resumed["current_step"] == "post_human_review"
    assert resumed["human_review_decision"] == "approve"
    assert resumed["human_review_notes"] == "Manual review completed."
    assert resumed["requires_human_review"] is False
    assert resumed["hitl_required"] is False
    assert "human_review" in resumed["completed_steps"]
    assert "post_human_review" in resumed["completed_steps"]
