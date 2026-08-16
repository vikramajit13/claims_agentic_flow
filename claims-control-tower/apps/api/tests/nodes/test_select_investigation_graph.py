from app.graph.builder import ClaimReviewGraphBuilder
from app.graph.state import ClaimGraphState
from app.nodes.select_investigation_graph import select_investigation_graph


def test_select_investigation_graph_prefers_document_evidence_when_ocr_exists():
    state = ClaimGraphState(
        claim_id=10,
        claim_documents=[
            {
                "document_id": 1,
                "document_type": "invoice",
                "document_url": "s3://claims/10/invoice.pdf",
                "uploaded_at": "2026-08-10T10:00:00+10:00",
                "status": "ocr_completed",
                "document_text": "Front bumper repair invoice",
                "normalized_document_type": "invoice",
            }
        ],
        risk_score=80,
        risk_level="HIGH",
    )

    result = select_investigation_graph(state)

    assert result["selected_investigation_graph"] == "document_evidence_graph"
    assert "document-focused investigation" in result["selected_investigation_reason"]


def test_select_investigation_graph_prefers_customer_history_for_high_risk_without_docs():
    state = ClaimGraphState(
        claim_id=11,
        customer_id=1001,
        risk_score=82,
        risk_level="HIGH",
    )

    result = select_investigation_graph(state)

    assert result["selected_investigation_graph"] == "customer_history_graph"


def test_claim_review_builder_routes_selected_graphs():
    route = ClaimReviewGraphBuilder._route_investigation_graph(
        ClaimGraphState(claim_id=12, selected_investigation_graph="document_evidence_graph")
    )

    assert route == "document_evidence_investigation"
