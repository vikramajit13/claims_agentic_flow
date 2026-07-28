import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.enums import DocumentStatus, OcrStatus
from app.graph.builder import ClaimReviewGraphBuilder
from app.graph.state import ClaimGraphState
from app.schemas.schemas import ClaimDocumentResponse


def _load_golden_cases() -> list[dict]:
    path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "golden_claim_graph_cases.json"
    )
    return json.loads(path.read_text())


def _to_document_response(document: dict) -> ClaimDocumentResponse:
    return ClaimDocumentResponse(
        id=document["id"],
        file_name=document["file_name"],
        content_type=document.get("content_type"),
        s3_uri=document["s3_uri"],
        s3_bucket=document["s3_bucket"],
        s3_key=document["s3_key"],
        upload_status=DocumentStatus(document["upload_status"]),
        ocr_requested=document.get("ocr_requested", True),
        ocr_status=OcrStatus(document["ocr_status"]),
        ocr_job_id=document.get("ocr_job_id"),
        ocr_error=document.get("ocr_error"),
        ocr_text=document.get("ocr_text"),
        normalized_text=document.get("normalized_text"),
        validation_results=document.get("validation_results"),
        document_classification=document.get("document_classification"),
        extracted_fields=document.get("extracted_fields"),
        quality_assessment=document.get("quality_assessment"),
        normalized_payload=document.get("normalized_payload"),
        normalized_document_type=document.get("normalized_document_type"),
        normalized_confidence=document.get("normalized_confidence"),
        normalized_at=document.get("normalized_at"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _to_claim_response(case: dict) -> SimpleNamespace:
    claim = case["claim"]
    return SimpleNamespace(
        description=claim.get("description"),
        claim_amount=claim.get("claim_amount"),
        claim_type=claim.get("claim_type"),
        incident_date=claim.get("incident_date"),
        documents=[_to_document_response(document) for document in claim.get("documents", [])],
    )


def _interrupt_value(result: dict) -> dict:
    interrupt = result["__interrupt__"][0]
    return getattr(interrupt, "value", interrupt)


def test_golden_claim_graph_cases():
    cases = _load_golden_cases()

    for case in cases:
        graph = ClaimReviewGraphBuilder().build().compile(checkpointer=InMemorySaver())
        initial_state = ClaimGraphState(claim_id=case["claim_id"])

        with patch("app.claim_service.ClaimService.get_claim", new_callable=AsyncMock) as mock_get_claim:
            mock_get_claim.return_value = _to_claim_response(case)

            result = asyncio.run(
                graph.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": case["thread_id"]}},
                )
            )

            expected = case["expected"]
            mode = expected["mode"]

            if mode == "completed":
                assert result["current_step"] == expected["current_step"], case["name"]
                assert result["risk_level"] == expected["risk_level"], case["name"]
                assert result["requires_human_review"] is expected["requires_human_review"], case["name"]
                for step in expected["completed_steps_include"]:
                    assert step in result["completed_steps"], case["name"]
                continue

            interrupt_payload = _interrupt_value(result)
            assert interrupt_payload["step"] == expected["interrupt_step"], case["name"]

            if mode == "interrupt":
                for error in expected["interrupt_errors_include"]:
                    assert error in interrupt_payload["errors"], case["name"]
                continue

            if mode == "resume":
                assert interrupt_payload["risk_level"] == expected["interrupt_risk_level"], case["name"]

                resumed = asyncio.run(
                    graph.ainvoke(
                        Command(resume=case["resume_payload"]),
                        config={"configurable": {"thread_id": case["thread_id"]}},
                    )
                )

                assert resumed["current_step"] == expected["resumed_current_step"], case["name"]
                assert resumed["human_review_decision"] == expected["human_review_decision"], case["name"]
                assert resumed["human_review_notes"] == expected["human_review_notes"], case["name"]
                for step in expected["completed_steps_include"]:
                    assert step in resumed["completed_steps"], case["name"]
                continue

            raise AssertionError(f"Unsupported golden eval mode: {mode}")
