from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.investigation_schema import ToolDecision, ToolExecutionRecord
from app.services.observability import traceable
from app.tool.tools import invoke_safe_read_tool


@traceable(name="execute_tool_node", run_type="tool")
def execute_tool_node(state: ClaimreviewState):
    selected_tool_decision = state.selected_tool_decision
    if selected_tool_decision is not None and isinstance(selected_tool_decision, dict):
        selected_tool_decision = ToolDecision(**selected_tool_decision)
    if selected_tool_decision is None or not selected_tool_decision.selected_tool:
        return {"latest_tool_result": None}

    tool_arguments = _enrich_tool_arguments(
        state,
        selected_tool_decision.selected_tool,
        selected_tool_decision.tool_arguments,
    )
    if selected_tool_decision.selected_tool == "get_prior_rejection_details" and not tool_arguments.get(
        "previous_claim_id"
    ):
        execution_record = ToolExecutionRecord(
            tool_name=selected_tool_decision.selected_tool,
            tool_arguments=tool_arguments,
            reason=selected_tool_decision.reason,
            result={},
        )
        return {"latest_tool_result": execution_record.dict()}

    result = invoke_safe_read_tool(
        selected_tool_decision.selected_tool,
        tool_arguments,
    )
    execution_record = ToolExecutionRecord(
        tool_name=selected_tool_decision.selected_tool,
        tool_arguments=tool_arguments,
        reason=selected_tool_decision.reason,
        result=result,
    )
    return {"latest_tool_result": execution_record.dict()}


def _enrich_tool_arguments(state: ClaimreviewState, tool_name: str, tool_arguments: dict) -> dict:
    case_packet = state.case_packet
    enriched = dict(tool_arguments or {})
    if tool_name == "get_claim_history":
        enriched.setdefault("customer_id", case_packet.claim_summary.customer_id)
        enriched.setdefault("lookback_days", 365)
        enriched.setdefault("exclude_claim_id", case_packet.claim_summary.claim_id)
    elif tool_name == "get_prior_rejection_details":
        enriched.setdefault("previous_claim_id", case_packet.claim_summary.previous_claim_id)
    elif tool_name == "get_policy_coverage_summary":
        enriched.setdefault("policy_id", case_packet.policy_summary.policy_id)
    elif tool_name == "get_document_metadata":
        enriched.setdefault("claim_id", case_packet.claim_summary.claim_id)
    elif tool_name == "get_guardrail_results":
        enriched.setdefault("claim_id", case_packet.claim_summary.claim_id)
        enriched.setdefault("workflow_run_id", case_packet.workflow_run_id)
        enriched.setdefault("phase", "PRE_ADJUDICATION_GUARDRAILS")
    return enriched
