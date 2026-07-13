from app.graph.state import ClaimGraphState


async def validate_claim_context(state: ClaimGraphState) -> dict:
    notes = list(state.notes)
    errors = list(state.errors)
    requires_human_review = bool(state.hitl_required)

    if not state.claim_description:
        errors.append("missing_claim_description")
        requires_human_review = True

    if state.claim_amount is None:
        errors.append("missing_claim_amount")
        requires_human_review = True

    if requires_human_review:
        notes.append("Claim context requires human review before graph continuation.")
        return {
            "current_step": "human_review",
            "requires_human_review": True,
            "hitl_required": True,
            "errors": errors,
            "notes": notes,
            "completed_steps": [*state.completed_steps, "process_claim", "validate_claim_context"],
        }

    notes.append("Claim context validated successfully.")
    return {
        "current_step": "context_validated",
        "requires_human_review": False,
        "hitl_required": False,
        "errors": errors,
        "notes": notes,
        "completed_steps": [*state.completed_steps, "process_claim", "validate_claim_context"],
    }
