from __future__ import annotations

from app.enums import NextWorkflowAction
from app.graph.state import ClaimGraphState


def recommend_next_action(state: ClaimGraphState) -> dict:
    if state.requires_human_review or state.hitl_required or state.risk_level == "HIGH":
        return {
            "current_step": "recommend_next_action",
            "recommended_next_action": NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value,
            "recommended_next_action_reason": "High risk or explicit HITL requirement detected.",
            "requires_human_review": True,
            "hitl_required": True,
            "completed_steps": [*state.completed_steps, "recommend_next_action"],
        }

    if any(error.startswith("missing_") for error in [*state.errors, *state.investigation_errors]):
        return {
            "current_step": "recommend_next_action",
            "recommended_next_action": NextWorkflowAction.REQUEST_MORE_INFO.value,
            "recommended_next_action_reason": "Missing claim context or investigation data requires more information.",
            "completed_steps": [*state.completed_steps, "recommend_next_action"],
        }

    guardrail_result = state.tool_results.get("get_guardrail_results")
    if isinstance(guardrail_result, dict) and guardrail_result.get("overall_decision") == "REVIEW_REQUIRED":
        return {
            "current_step": "recommend_next_action",
            "recommended_next_action": NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value,
            "recommended_next_action_reason": "Deterministic guardrails require human review.",
            "requires_human_review": True,
            "hitl_required": True,
            "completed_steps": [*state.completed_steps, "recommend_next_action"],
        }

    prior_rejections = state.tool_results.get("get_prior_rejection_details")
    if isinstance(prior_rejections, dict) and prior_rejections.get("prior_rejection_count", 0) > 0:
        return {
            "current_step": "recommend_next_action",
            "recommended_next_action": NextWorkflowAction.BLOCK_RECOMMENDED.value,
            "recommended_next_action_reason": "Prior rejected claim history warrants manual block recommendation.",
            "completed_steps": [*state.completed_steps, "recommend_next_action"],
        }

    return {
        "current_step": "recommend_next_action",
        "recommended_next_action": NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value,
        "recommended_next_action_reason": "Claim has sufficient context to continue beyond investigation.",
        "completed_steps": [*state.completed_steps, "recommend_next_action"],
    }
