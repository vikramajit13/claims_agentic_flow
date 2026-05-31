from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.investigation_schema import InformationGap, ToolDecision
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService
from app.services.observability import traceable


@traceable(name="agent_decide_tool_node", run_type="chain")
def agent_decide_tool_node(state: ClaimreviewState):
    information_gaps = [
        gap if isinstance(gap, InformationGap) else InformationGap(**gap)
        for gap in state.information_gaps
    ]
    prompt = PromptService().generate_tool_decision_prompt(
        information_gaps,
        state.previous_tool_calls,
        state.available_tools,
        state.case_packet,
    )
    fallback = _build_fallback_tool_decision(state, information_gaps)
    decision = OllamaAsyncService().generate_structured(prompt, fallback.dict())
    selected_tool = decision.get("selected_tool")
    if selected_tool and selected_tool not in state.available_tools:
        decision = fallback.dict()
    return {"selected_tool_decision": decision}


def _build_fallback_tool_decision(state: ClaimreviewState, information_gaps: list[InformationGap]) -> ToolDecision:
    previous_tool_names = {call.tool_name if hasattr(call, "tool_name") else call.get("tool_name") for call in state.previous_tool_calls}
    for gap in information_gaps:
        if gap.suggested_tool not in state.available_tools:
            continue
        if gap.suggested_tool in previous_tool_names:
            continue
        return ToolDecision(
            selected_tool=gap.suggested_tool,
            tool_arguments=_tool_arguments_for_gap(state, gap.suggested_tool),
            reason=gap.gap,
        )
    return ToolDecision(
        selected_tool=None,
        tool_arguments={},
        reason="No additional permitted read-only tool call is required.",
    )


def _tool_arguments_for_gap(state: ClaimreviewState, tool_name: str) -> dict:
    case_packet = state.case_packet
    if tool_name == "get_claim_history":
        return {
            "customer_id": case_packet.claim_summary.customer_id,
            "lookback_days": 365,
            "exclude_claim_id": case_packet.claim_summary.claim_id,
        }
    if tool_name == "get_prior_rejection_details":
        return {"previous_claim_id": case_packet.claim_summary.previous_claim_id}
    if tool_name == "get_policy_coverage_summary":
        return {"policy_id": case_packet.policy_summary.policy_id}
    if tool_name == "get_document_metadata":
        requested_types = [
            document.get("document_type")
            for document in case_packet.documents
            if document.get("document_type") in {"invoice", "repair_estimate", "police_report", "medical_report"}
        ]
        return {
            "claim_id": case_packet.claim_summary.claim_id,
            "document_types": requested_types or None,
        }
    if tool_name == "get_guardrail_results":
        return {
            "claim_id": case_packet.claim_summary.claim_id,
            "workflow_run_id": case_packet.workflow_run_id,
            "phase": "PRE_ADJUDICATION_GUARDRAILS",
        }
    return {}
