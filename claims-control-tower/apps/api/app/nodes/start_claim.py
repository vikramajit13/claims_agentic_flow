from app.claim_service import ClaimService
from app.graph.state import ClaimGraphState
from app.mappers.document_mapper import map_claim_documents_response


async def process_claim(state: ClaimGraphState) -> dict:
    claim_service = ClaimService()
    claim = await claim_service.get_claim(state.claim_id)

    return {
        "claim_id": state.claim_id,
        "graph_name": state.graph_name,
        "graph_version": state.graph_version,
        "graph_run_id": state.graph_run_id,
        "claim_status": "ready_for_graph",
        "current_step": "graph_bootstrap",
        "incident_date": claim.incident_date,
        "claim_description": claim.description,
        "claim_amount": claim.claim_amount,
        "claim_type": claim.claim_type,
        "execution_plan": ["graph_bootstrap", "validate_claim_context", "analyse_risk"],
        "claim_documents": map_claim_documents_response(claim.documents),
        "notes": [*state.notes, "Claim loaded into graph state"],
    }
