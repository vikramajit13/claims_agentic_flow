from app.tools.read_only_claim_tools import (
    get_claim_history,
    get_document_metadata,
    get_guardrail_results,
    get_policy_coverage_summary,
    get_prior_rejection_details,
)

SAFE_READ_ONLY_TOOLS = {
    "get_claim_history": get_claim_history,
    "get_prior_rejection_details": get_prior_rejection_details,
    "get_policy_coverage_summary": get_policy_coverage_summary,
    "get_document_metadata": get_document_metadata,
    "get_guardrail_results": get_guardrail_results,
}

__all__ = [
    "SAFE_READ_ONLY_TOOLS",
    "get_claim_history",
    "get_prior_rejection_details",
    "get_policy_coverage_summary",
    "get_document_metadata",
    "get_guardrail_results",
]
