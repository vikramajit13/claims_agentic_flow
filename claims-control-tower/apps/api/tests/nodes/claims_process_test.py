import asyncio

import pytest
from unittest.mock import AsyncMock, patch

from app.enums import DocumentStatus, OcrStatus
from app.graph.state import ClaimGraphState
from app.nodes.start_claim import process_claim
from app.schemas.schemas import ClaimDocumentResponse


@patch("app.claim_service.ClaimService.get_claim", new_callable=AsyncMock)
def test_process_claim(mock_get_claim):
    state = ClaimGraphState(
        claim_id=12345,
        graph_name="test_graph",
        graph_version="1.0",
        graph_run_id="run_001",
        notes=[],
        completed_steps=[],
    )

    mock_get_claim.return_value = AsyncMock(
        description="Test claim",
        claim_amount=100,
        claim_type="type_a",
        documents=[
            ClaimDocumentResponse(
                id=7,
                file_name="accident-photo.jpg",
                content_type="image/jpeg",
                s3_uri="s3://claims-bucket/claims/123/accident-photo.jpg",
                s3_bucket="claims-bucket",
                s3_key="claims/123/accident-photo.jpg",
                upload_status=DocumentStatus.UPLOADED,
                ocr_requested=False,
                ocr_status=OcrStatus.NOT_REQUESTED,
                ocr_job_id=None,
                ocr_error=None,
                ocr_text=None,
                normalized_text=None,
                validation_results=None,
                document_classification={"document_type": "PHOTO"},
                normalised_document_type="photo",
                extracted_fields=None,
                quality_assessment=None,
                created_at="2026-07-16T10:00:00+10:00",
                updated_at="2026-07-16T10:05:00+10:00",
            )
        ],
    )


    result = asyncio.run(process_claim(state))

    assert result["claim_id"] == 12345
    assert result["graph_name"] == "test_graph"
    assert result["graph_version"] == "1.0"
    assert result["graph_run_id"] == "run_001"
    assert result["claim_status"] == "ready_for_graph"
    assert result["current_step"] == "graph_bootstrap"
    assert result["execution_plan"] == ["graph_bootstrap", "validate_claim_context", "analyse_risk"]
    assert result["claim_documents"][0].document_id == 7
    assert result["claim_documents"][0].document_type == "PHOTO"
    assert result["claim_documents"][0].document_url == "s3://claims-bucket/claims/123/accident-photo.jpg"
    assert "Claim loaded into graph state" in result["notes"]
