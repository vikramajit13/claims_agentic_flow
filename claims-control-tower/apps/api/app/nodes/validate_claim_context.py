from __future__ import annotations

from app.common.const import CLAIM_TYPE_DOCUMENT_REQUIREMENTS
from app.common.utils import normalize_claim_type
from app.graph.state import ClaimGraphState


async def validate_claim_context(state: ClaimGraphState) -> dict:
    notes = list(state.notes)
    errors = list(state.errors)
    claim_type = normalize_claim_type(state.claim_type)
    required_documents = CLAIM_TYPE_DOCUMENT_REQUIREMENTS.get(claim_type, [])
    observed_documents = [
        str(
            document.normalized_document_type
            or (document.normalized_payload or {}).get("document_type")
            or document.document_type
        ).lower()
        for document in state.claim_documents
    ]

    if not state.claim_description:
        errors.append("missing_claim_description")

    if state.claim_amount is None:
        errors.append("missing_claim_amount")

    if not state.claim_documents:
        errors.append("missing_claim_documents")

    if errors:
        notes.append("Claim context is incomplete; graph should stop before risk analysis.")
        return {
            "current_step": "context_invalid",
            "requires_human_review": True,
            "hitl_required": True,
            "errors": errors,
            "notes": notes,
            "required_documents": required_documents,
            "observed_documents": observed_documents,
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
        "required_documents": required_documents,
        "observed_documents": observed_documents,
        "completed_steps": [
            *state.completed_steps,
            "process_claim",
            "validate_claim_context",
        ],
    }
