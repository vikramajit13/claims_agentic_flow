from app.graph.state import ClaimGraphState


async def human_in_the_loop_review(state: ClaimGraphState) -> dict:
    notes = list(state.notes)
    notes.append("Graph entered the human review checkpoint.")
    return {
        "current_step": "human_review",
        "requires_human_review": True,
        "hitl_required": True,
        "notes": notes,
        "completed_steps": [*state.completed_steps, "process_claim", "validate_claim_context", "analyse_risk", "human_review"],
    }
