from langchain.tools import tool, ToolRuntime
from app.services.claims_system_adapter import ClaimsSystemAdapter


def create_risk_tools(claims_adapter: ClaimsSystemAdapter):
    @tool(
        name_or_callable="get_claim_history",
        description="Fetch the claim history for a given customer ID, including past claims, outcomes, and any relevant notes.",
    )
    def get_claim_history(
        lookback_months: int,
        runtime: ToolRuntime,
    ) -> dict:
        """
        Fetch the claim history for a given customer ID.

        Args:
            customer_id (int): The ID of the customer to fetch claim history for.

        Returns:
            dict: A dictionary containing the claim history, including past claims, outcomes, and any relevant notes.
        """
        case_packet = runtime.state["case_packet"]
        claim = case_packet.claim_summary

        return claims_adapter.get_recent_claims(
            customer_id=claim.customer_id,
            lookback_days=lookback_months * 30,  # Convert months to days
            exclude_claim_id=claim.claim_id,
        )
    return [get_claim_history]
