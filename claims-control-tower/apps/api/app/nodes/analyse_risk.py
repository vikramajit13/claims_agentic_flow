
from app.graph.state import ClaimGraphState
from app.claim_service import ClaimService


def analyse_risk(state: ClaimGraphState) -> dict:
    # Perform risk analysis on the claim
    # This could involve checking for fraud indicators, assessing claim validity, etc.
    claimid = state.claim_id
    
    service = ClaimService()
    claim_data = service.get_claim(claimid)

    risk_level = "low"
    if claim_data:
        # Perform analysis based on claim data
        if claim_data.fraud_suspected:
            risk_level = "high"
        elif claim_data.claim_amount > 10000:
            risk_level = "medium"

    return {
        "current_step": "risk_analysis",
        "risk_level": risk_level,
        "notes": [],
        "completed_steps": [
            *state.completed_steps,
            "process_claim",
            "validate_claim_context",
        ],
    }
