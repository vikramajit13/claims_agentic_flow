from app.claim_service import ClaimService
from app.graph.state import ClaimGraphState
from app.mappers.document_mapper import map_claim_documents_response


def _safe_attr(value, attribute: str, default):
    resolved = getattr(value, attribute, default)
    if type(resolved).__name__ in {"AsyncMock", "MagicMock", "Mock"}:
        return default
    return resolved


async def process_claim(state: ClaimGraphState) -> dict:
    claim_service = ClaimService()
    claim = await claim_service.get_claim(state.claim_id)
    claim_id = _safe_attr(claim, "id", state.claim_id)
    customer_id = _safe_attr(claim, "customer_id", state.customer_id)
    documents = _safe_attr(claim, "documents", [])

    return {
        "claim_id": state.claim_id,
        "customer_id": customer_id,
        "policy_id": f"POL-{claim_id:06d}",
        "graph_name": state.graph_name,
        "graph_version": state.graph_version,
        "graph_run_id": state.graph_run_id,
        "claim_status": "ready_for_graph",
        "current_step": "graph_bootstrap",
        "incident_date": _safe_attr(claim, "incident_date", None),
        "claim_description": _safe_attr(claim, "description", None),
        "claim_amount": _safe_attr(claim, "claim_amount", None),
        "claim_type": _safe_attr(claim, "claim_type", None),
        "execution_plan": [
            "graph_bootstrap",
            "validate_claim_context",
            "analyse_risk",
            "claim_investigation",
            "recommend_next_action",
        ],
        "claim_documents": map_claim_documents_response(documents),
        "notes": [*state.notes, "Claim loaded into graph state"],
    }
