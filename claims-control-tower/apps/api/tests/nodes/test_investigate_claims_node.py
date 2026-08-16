from app.graph.state import ClaimGraphState
from app.nodes.investigate_claims_node import build_investigation_tool_calls, claim_investigation_agent


def test_customer_history_graph_selects_customer_tools():
    state = ClaimGraphState(
        claim_id=10,
        customer_id=1001,
        graph_name="customer_history_graph",
    )

    tool_calls = build_investigation_tool_calls(state)
    tool_names = [tool_call["name"] for tool_call in tool_calls]

    assert "get_claim_history" in tool_names
    assert "get_prior_rejection_details" in tool_names
    assert "get_customer_risk_overview" in tool_names
    assert "get_claim_timeline" in tool_names
    assert "get_document_metadata" not in tool_names


def test_document_evidence_graph_selects_document_tools():
    state = ClaimGraphState(
        claim_id=11,
        graph_name="document_evidence_graph",
        claim_documents=[
            {
                "document_id": 1,
                "document_type": "invoice",
                "document_url": "s3://claims/11/invoice.pdf",
                "uploaded_at": "2026-08-10T10:00:00+10:00",
                "status": "ocr_completed",
            }
        ],
    )

    tool_calls = build_investigation_tool_calls(state)
    tool_names = [tool_call["name"] for tool_call in tool_calls]

    assert "get_document_metadata" in tool_names
    assert "get_document_text_evidence" in tool_names
    assert "get_guardrail_results" in tool_names
    assert "get_claim_timeline" in tool_names
    assert "get_claim_history" not in tool_names


def test_claim_investigation_agent_exposes_tool_and_graph_catalogs():
    state = ClaimGraphState(
        claim_id=12,
        customer_id=1001,
        graph_name="customer_history_graph",
    )

    result = claim_investigation_agent(state)

    assert result["investigation_required"] is True
    assert any(item["name"] == "get_customer_risk_overview" for item in result["tool_catalog"])
    assert any(item["graph_name"] == "document_evidence_graph" for item in result["graph_catalog"])
