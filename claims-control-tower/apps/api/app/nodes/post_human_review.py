from app.graph.state import ClaimGraphState


async def post_human_review(state: ClaimGraphState) -> dict:
    notes = list(state.notes)
    notes.append("Human review response recorded. Workflow ends after post-review handling for now.")
    return {
        "current_step": "post_human_review",
        "notes": notes,
        "completed_steps": [
            *state.completed_steps,
            "process_claim",
            "validate_claim_context",
            "analyse_risk",
            "human_review",
            "post_human_review",
        ],
    }
