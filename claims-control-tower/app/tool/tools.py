from langchain_core.tools import tool
from app.services.observability import traceable
from app.models.workflow_event import WorkflowEventType
from app.repositories.claim_repository import ClaimRepository
from app.repositories.policy_repository import PolicyRepository
from app.services.audit_service import AuditService
from app.services.claim_service import ClaimService


@tool(
    name_or_callable="get_claim_history",
    description="Fetch the claim history for a given customer ID, including past claims, outcomes, and any relevant notes.",
)
@traceable(name="get_claim_history_tool", run_type="tool")
def get_claim_history(
    customer_id: int, lookback_days: int, exclude_claim_id: int
) -> dict:
    """
    Fetch the claim history for a given customer ID.

    Args:
        customer_id (int): The ID of the customer to fetch claim history for.

    Returns:
        dict: A dictionary containing the claim history, including past claims, outcomes, and any relevant notes.
    """
    # TODO: Implement the logic to fetch claim history
    claim_repository = ClaimRepository()
    claim_history = claim_repository.get_recent_customer_claims(
        customer_id, lookback_days, exclude_claim_id
    )
    prior_claims = [
        {
            "claim_id": claim.id,
            "claim_type": claim.claim_type,
            "claim_date": claim.incident_date,
            "claim_amount": claim.claim_amount,
            "status": claim.status,
        }
        for claim in claim_history
    ]

    return {
        "customer_id": customer_id,
        "lookback_days": lookback_days,
        "prior_claims": prior_claims,
        "prior_claims_count": len(prior_claims),
    }


@tool(
    name_or_callable="get_prior_rejection_details",
    description="Fetch the prior rejection details for a given claim ID.",
)
@traceable(name="get_prior_rejection_details_tool", run_type="tool")
def get_prior_rejection_details(previous_claim_id: int) -> dict:
    """
    Fetch the prior rejection details for a given claim ID.

    Args:
        previous_claim_id (int): The ID of the previous claim to fetch rejection details for.

    Returns:
        dict: A dictionary containing the prior rejection details, if available.
    """
    claim_repository = ClaimRepository()
    previous_claim = claim_repository.get(previous_claim_id)
    if not previous_claim:
        return {}

    status_keys = {
        "REJECTED": "rejected_at",
        "APPROVED": "approved_at",
        "SUBMITTED": "submitted_at",
        "IN_REVIEW": "in_review_at",
        "PENDING_HUMAN_REVIEW": "pending_human_review_at",
        "PENDING_MORE_INFO": "pending_more_info_at",
        "PAYMENT_READY": "payment_ready_at",
        "PAYMENT_BLOCKED": "payment_blocked_at",
        "COMPLETED": "completed_at",
    }

    timestamp_key = status_keys.get(previous_claim.status)
    return {
        "claim_id": previous_claim.id,
        "claim_status": previous_claim.status,
        **({timestamp_key: previous_claim.updated_at} if timestamp_key else {}),
    }


@tool(
    name_or_callable="get_policy_coverage_summary",
    description="Fetch policy dates, status, limits, deductibles, and covered claim types for policy interpretation and coverage reasoning.",
)
@traceable(name="get_policy_coverage_summary_tool", run_type="tool")
def get_policy_coverage_summary(policy_id: int) -> dict:
    policy_repository = PolicyRepository()
    policy = policy_repository.get(policy_id)
    return {
        "policy_id": policy.policy_number,
        "status": policy.status.upper(),
        "active_from": policy.active_from,
        "active_to": policy.active_to,
        "coverage_limit": policy.coverage_limit,
        "deductible": policy.deductible,
        "covered_claim_types": [claim_type.upper() for claim_type in policy.covered_claim_types],
    }


@tool(
    name_or_callable="get_document_metadata",
    description="Fetch structured claim document metadata for evidence analysis, including invoice fields and verification status.",
)
@traceable(name="get_document_metadata_tool", run_type="tool")
def get_document_metadata(claim_id: int, document_types: list[str] | None = None) -> dict:
    claim_service = ClaimService()
    documents = claim_service.get_claim_documents(claim_id)
    normalized_types = {document_type.lower() for document_type in document_types} if document_types else None
    filtered_documents = [
        document
        for document in documents
        if normalized_types is None or document.document_type.value.lower() in normalized_types
    ]

    return {
        "claim_id": claim_id,
        "documents": [
            {
                "document_id": document.id,
                "document_type": document.document_type.value.upper(),
                "invoice_date": document.document_metadata.get("invoice_date"),
                "invoice_amount": document.document_metadata.get("invoice_amount"),
                "vendor_name": document.document_metadata.get("vendor_name"),
                "verification_status": document.verification_status.value.upper(),
                "document_metadata": document.document_metadata,
            }
            for document in filtered_documents
        ],
    }


@tool(
    name_or_callable="get_guardrail_results",
    description="Fetch deterministic business guardrail outcomes for a claim from stored workflow events.",
)
@traceable(name="get_guardrail_results_tool", run_type="tool")
def get_guardrail_results(
    claim_id: int,
    workflow_run_id: int,
    phase: str | None = None,
) -> dict:
    audit_service = AuditService()
    workflow_events = audit_service.get_workflow_events(workflow_run_id)
    guardrail_events = [
        event
        for event in workflow_events
        if event.claim_id == claim_id and event.event_type == WorkflowEventType.BUSINESS_GUARDRAILS_EVALUATED
    ]
    if phase:
        normalized_phase = phase.upper()
        guardrail_events = [
            event for event in guardrail_events if event.step_name.upper() == normalized_phase
        ]
    if not guardrail_events:
        return {"overall_decision": None, "results": []}

    latest_event = guardrail_events[-1]
    payload = latest_event.event_payload
    return {
        "overall_decision": payload.get("overall_decision"),
        "results": [
            {
                "code": result.get("code"),
                "decision": result.get("decision"),
                "severity": result.get("severity"),
                "message": result.get("message"),
                "category": result.get("category"),
                "details": result.get("details", {}),
            }
            for result in payload.get("results", [])
        ],
    }


SAFE_READ_ONLY_TOOLS = {
    "get_claim_history": get_claim_history,
    "get_prior_rejection_details": get_prior_rejection_details,
    "get_policy_coverage_summary": get_policy_coverage_summary,
    "get_document_metadata": get_document_metadata,
    "get_guardrail_results": get_guardrail_results,
}


@traceable(name="invoke_safe_read_tool", run_type="tool")
def invoke_safe_read_tool(tool_name: str, arguments: dict) -> dict:
    if tool_name not in SAFE_READ_ONLY_TOOLS:
        raise ValueError(f"Tool '{tool_name}' is not in the permitted read-only tool registry.")
    return SAFE_READ_ONLY_TOOLS[tool_name].invoke(arguments)
