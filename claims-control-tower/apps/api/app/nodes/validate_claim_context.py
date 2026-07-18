from app.graph.state import ClaimGraphState
from app.enum.enums import ClaimType
from app.common.const import document_required

# Confirm the required doc set for the claim type
# Verify each required document exists in state
# Check OCR/normalization completed successfully
# Validate invoice metadata like invoice date, amount, vendor, and currency
# Validate image metadata like file type, readability, and confidence
# Compare document dates against incident date
# Compare claim amount against invoice amount and policy limits if already loaded
# Mark gaps or contradictions as REQUEST_MORE_INFO or HUMAN_REVIEW


async def validate_claim_context(state: ClaimGraphState) -> dict:
    notes = list(state.notes)
    errors = list(state.errors)
    requires_human_review = bool(state.hitl_required)
    # check if documents are present as per claim_type requirements

    claim_type: ClaimType | None = (
        ClaimType(state.claim_type) if state.claim_type else None
    )
    docs_required = document_required.get(claim_type, []) if claim_type else []

    for document in state.claim_documents:
        if docs_required and document.document_type not in docs_required:
            errors.append(f"unexpected_document:{document.document_id}")
            requires_human_review = True

        if str(document.ocr_status).lower() == "failed":
            errors.append(f"document_ocr_failed:{document.document_id}")
            requires_human_review = True

        if (
            str(document.status).lower() == "ocr_completed"
            and not document.document_text
        ):
            errors.append(f"missing_document_text:{document.document_id}")
            requires_human_review = True

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
            "completed_steps": [
                *state.completed_steps,
                "process_claim",
                "validate_claim_context",
            ],
        }

    notes.append("Claim context validated successfully.")
    return {
        "current_step": "context_validated",
        "requires_human_review": False,
        "hitl_required": False,
        "errors": errors,
        "notes": notes,
        "completed_steps": [
            *state.completed_steps,
            "process_claim",
            "validate_claim_context",
        ],
    }
