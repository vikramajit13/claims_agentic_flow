import json

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.builder import BaseToolGraphBuilder, ClaimReviewGraphBuilder
from app.graph.state import ClaimGraphState
from app.nodes.select_investigation_graph import (
    build_graph_selection_tool_calls,
    merge_selected_investigation_graph,
    select_investigation_graph,
)


def test_graph_selector_agent_emits_specialist_tool_calls():
    state = ClaimGraphState(
        claim_id=10,
        policy_id="POL-000010",
        claim_amount=6800,
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
        customer_id=1001,
    )

    result = select_investigation_graph(state)
    message = result["messages"][0]

    assert isinstance(message, AIMessage)
    tool_names = [call["name"] for call in message.tool_calls]
    assert tool_names == [
        "recommend_document_evidence_graph",
        "recommend_guardrail_review_graph",
        "recommend_customer_history_graph",
        "recommend_policy_coverage_graph",
        "recommend_broad_investigation_graph",
    ]


def test_build_graph_selection_tool_calls_includes_fallback():
    state = ClaimGraphState(
        claim_id=11,
        risk_score=15,
        risk_level="LOW",
    )

    tool_calls = build_graph_selection_tool_calls(state)

    assert [tool_call["name"] for tool_call in tool_calls] == ["recommend_broad_investigation_graph"]


def test_merge_selected_investigation_graph_picks_highest_priority_recommendation():
    state = ClaimGraphState(
        claim_id=12,
        investigation_notes=["selector started"],
        messages=[
            ToolMessage(
                content=json.dumps(
                    {
                        "graph_name": "policy_coverage_graph",
                        "reason": "Policy coverage and deductible validation can shape the final recommendation.",
                        "priority": 70,
                        "recommended": True,
                    }
                ),
                tool_call_id="tool-1",
                name="recommend_policy_coverage_graph",
            ),
            ToolMessage(
                content=json.dumps(
                    {
                        "graph_name": "document_evidence_graph",
                        "reason": "OCR or normalized evidence is already available and should be inspected first.",
                        "priority": 100,
                        "recommended": True,
                    }
                ),
                tool_call_id="tool-2",
                name="recommend_document_evidence_graph",
            ),
        ],
    )

    result = merge_selected_investigation_graph(state)

    assert result["selected_investigation_graph"] == "document_evidence_graph"
    assert result["investigation_plan"][0]["graph_name"] == "policy_coverage_graph"
    assert result["investigation_plan"][1]["graph_name"] == "document_evidence_graph"


def test_claim_review_builder_routes_selected_graphs():
    route = ClaimReviewGraphBuilder._route_investigation_graph(
        ClaimGraphState(claim_id=13, selected_investigation_graph="document_evidence_graph")
    )

    assert route == "document_evidence_investigation"


def test_claim_review_builder_routes_guardrail_graph():
    route = ClaimReviewGraphBuilder._route_investigation_graph(
        ClaimGraphState(claim_id=14, selected_investigation_graph="guardrail_review_graph")
    )

    assert route == "guardrail_review_investigation"


def test_claim_review_builder_routes_to_selection_toolnode():
    state = ClaimGraphState(
        claim_id=15,
        messages=[
            AIMessage(
                content="Selecting graph",
                tool_calls=[{"name": "recommend_broad_investigation_graph", "args": {"reason": "fallback"}, "id": "tool-9", "type": "tool_call"}],
            )
        ],
    )

    route = ClaimReviewGraphBuilder._route_after_graph_selection_agent(state)

    assert route == "investigation_selection_tools"


def test_investigation_builder_routes_to_judge_before_toolnode():
    state = ClaimGraphState(
        claim_id=16,
        messages=[
            AIMessage(
                content="Investigating tools",
                tool_calls=[{"name": "get_claim_history", "args": {}, "id": "tool-10", "type": "tool_call"}],
            )
        ],
    )

    route = BaseToolGraphBuilder._route_after_investigation_agent(state)

    assert route == "judge_tool_selection"
