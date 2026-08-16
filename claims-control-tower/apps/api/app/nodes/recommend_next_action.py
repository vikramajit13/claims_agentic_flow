from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from app.enums import NextWorkflowAction
from app.graph.state import ClaimGraphState


ACTION_TOOL_MAP = {
    NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value: "recommend_human_review_action",
    NextWorkflowAction.REQUEST_MORE_INFO.value: "recommend_request_more_info_action",
    NextWorkflowAction.BLOCK_RECOMMENDED.value: "recommend_block_claim_action",
    NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value: "recommend_proceed_to_payment_action",
}
ACTION_TOOL_NAMES = set(ACTION_TOOL_MAP.values())


def _tool_call(name: str, reason: str, priority: int, confidence: float) -> dict[str, Any]:
    return {
        "name": name,
        "args": {
            "reason": reason,
            "priority": priority,
            "confidence": confidence,
        },
        "id": f"tool-{uuid4()}",
        "type": "tool_call",
    }


def build_action_recommendation_tool_calls(state: ClaimGraphState) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []

    if state.requires_human_review or state.hitl_required or state.risk_level == "HIGH":
        tool_calls.append(
            _tool_call(
                ACTION_TOOL_MAP[NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value],
                "High risk or explicit HITL requirement detected.",
                100,
                0.96,
            )
        )

    if any(error.startswith("missing_") for error in [*state.errors, *state.investigation_errors]):
        tool_calls.append(
            _tool_call(
                ACTION_TOOL_MAP[NextWorkflowAction.REQUEST_MORE_INFO.value],
                "Missing claim context or investigation data requires more information.",
                95,
                0.91,
            )
        )

    guardrail_result = state.tool_results.get("get_guardrail_results")
    if isinstance(guardrail_result, dict) and guardrail_result.get("overall_decision") == "REVIEW_REQUIRED":
        tool_calls.append(
            _tool_call(
                ACTION_TOOL_MAP[NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value],
                "Deterministic guardrails require human review.",
                98,
                0.93,
            )
        )

    prior_rejections = state.tool_results.get("get_prior_rejection_details")
    if isinstance(prior_rejections, dict) and prior_rejections.get("prior_rejection_count", 0) > 0:
        tool_calls.append(
            _tool_call(
                ACTION_TOOL_MAP[NextWorkflowAction.BLOCK_RECOMMENDED.value],
                "Prior rejected claim history warrants manual block recommendation.",
                90,
                0.86,
            )
        )

    if not tool_calls:
        tool_calls.append(
            _tool_call(
                ACTION_TOOL_MAP[NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value],
                "Claim has sufficient context to continue beyond investigation.",
                70,
                0.82,
            )
        )

    return tool_calls


def recommend_next_action(state: ClaimGraphState) -> dict[str, Any]:
    tool_calls = build_action_recommendation_tool_calls(state)
    notes = list(state.notes)
    notes.append(f"Action agent proposed {len(tool_calls)} action recommendation tool call(s).")
    return {
        "current_step": "recommend_next_action",
        "notes": notes,
        "messages": [AIMessage(content="Selecting the best workflow next action.", tool_calls=tool_calls)],
    }


def merge_recommended_action(state: ClaimGraphState) -> dict[str, Any]:
    recommended_action = NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value
    recommended_reason = "Claim has sufficient context to continue beyond investigation."
    best_priority = -1
    requires_human_review = state.requires_human_review
    hitl_required = state.hitl_required
    saw_action_message = False

    for message in state.messages:
        if not isinstance(message, ToolMessage):
            continue
        if message.name not in ACTION_TOOL_NAMES:
            continue
        try:
            payload = json.loads(message.content)
        except json.JSONDecodeError:
            continue

        saw_action_message = True
        priority = int(payload.get("priority") or 0)
        action = str(payload.get("action") or recommended_action)
        if payload.get("recommended") and priority > best_priority:
            best_priority = priority
            recommended_action = action
            recommended_reason = str(payload.get("reason") or recommended_reason)

    if not saw_action_message:
        if state.requires_human_review or state.hitl_required or state.risk_level == "HIGH":
            recommended_action = NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value
            recommended_reason = "High risk or explicit HITL requirement detected."
        elif any(error.startswith("missing_") for error in [*state.errors, *state.investigation_errors]):
            recommended_action = NextWorkflowAction.REQUEST_MORE_INFO.value
            recommended_reason = "Missing claim context or investigation data requires more information."
        else:
            guardrail_result = state.tool_results.get("get_guardrail_results")
            prior_rejections = state.tool_results.get("get_prior_rejection_details")
            if isinstance(guardrail_result, dict) and guardrail_result.get("overall_decision") == "REVIEW_REQUIRED":
                recommended_action = NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value
                recommended_reason = "Deterministic guardrails require human review."
            elif isinstance(prior_rejections, dict) and prior_rejections.get("prior_rejection_count", 0) > 0:
                recommended_action = NextWorkflowAction.BLOCK_RECOMMENDED.value
                recommended_reason = "Prior rejected claim history warrants manual block recommendation."

    if recommended_action == NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value:
        requires_human_review = True
        hitl_required = True

    return {
        "current_step": "recommend_next_action",
        "recommended_next_action": recommended_action,
        "recommended_next_action_reason": recommended_reason,
        "requires_human_review": requires_human_review,
        "hitl_required": hitl_required,
        "completed_steps": [*state.completed_steps, "recommend_next_action"],
    }
