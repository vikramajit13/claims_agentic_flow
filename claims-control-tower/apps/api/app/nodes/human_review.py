from langgraph.types import Command, interrupt

from app.graph.state import ClaimGraphState


async def human_in_the_loop_review(state: ClaimGraphState) -> dict:
    review_request = {
        "step": "human_review",
        "claim_id": state.claim_id,
        "risk_score": state.risk_score,
        "risk_level": state.risk_level,
        "risk_factors": state.risk_factors,
        "errors": state.errors,
        "message": "Human review required. Resume with Command(resume=...) after reviewer decision.",
    }
    human_response = interrupt(review_request)
    notes = list(state.notes)
    notes.append("Graph entered the human review checkpoint.")
    response_payload = human_response if isinstance(human_response, dict) else {"value": human_response}
    decision = response_payload.get("decision") or response_payload.get("type")
    reviewer_notes = response_payload.get("notes") or response_payload.get("comment")
    return Command(
        update={
            "current_step": "human_review",
            "requires_human_review": False,
            "hitl_required": False,
            "human_review_request": review_request,
            "human_review_response": response_payload,
            "human_review_decision": str(decision) if decision is not None else None,
            "human_review_notes": str(reviewer_notes) if reviewer_notes is not None else None,
            "notes": notes,
            "completed_steps": [
                *state.completed_steps,
                "process_claim",
                "validate_claim_context",
                "analyse_risk",
                "human_review",
            ],
        },
        goto="post_human_review",
    )
