import asyncio
from unittest.mock import patch

from langgraph.types import Command

from app.graph.state import ClaimGraphState
from app.nodes.human_review import human_in_the_loop_review


def test_human_review_node_returns_resume_command():
    state = ClaimGraphState(
        claim_id=42,
        risk_score=85,
        risk_level="HIGH",
        risk_factors=["invoice_after_incident:7", "low_confidence_document:7"],
        errors=["invoice_after_incident:7"],
        notes=["Risk analysis recommends human review before payment routing."],
        completed_steps=["process_claim", "validate_claim_context", "analyse_risk"],
        requires_human_review=True,
        hitl_required=True,
    )

    with patch(
        "app.nodes.human_review.interrupt",
        return_value={"decision": "approve", "notes": "Reviewed and accepted."},
    ):
        result = asyncio.run(human_in_the_loop_review(state))

    assert isinstance(result, Command)
    assert result.goto == "post_human_review"
    assert result.update["current_step"] == "human_review"
    assert result.update["requires_human_review"] is False
    assert result.update["hitl_required"] is False
    assert result.update["human_review_decision"] == "approve"
    assert result.update["human_review_notes"] == "Reviewed and accepted."
    assert result.update["human_review_request"]["step"] == "human_review"
    assert result.update["human_review_request"]["claim_id"] == 42
    assert "Graph entered the human review checkpoint." in result.update["notes"]

