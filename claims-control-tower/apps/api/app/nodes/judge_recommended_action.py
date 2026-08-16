from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage

from app.config import settings
from app.enums import NextWorkflowAction
from app.graph.state import ClaimGraphState
from app.llm_client import LLMClient
from app.prompt_loader import load_prompt_artifact, render_prompt_template


AVAILABLE_ACTIONS = [
    NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value,
    NextWorkflowAction.REQUEST_MORE_INFO.value,
    NextWorkflowAction.BLOCK_RECOMMENDED.value,
    NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value,
]

ACTION_TOOL_MAP = {
    NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value: "recommend_human_review_action",
    NextWorkflowAction.REQUEST_MORE_INFO.value: "recommend_request_more_info_action",
    NextWorkflowAction.BLOCK_RECOMMENDED.value: "recommend_block_claim_action",
    NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value: "recommend_proceed_to_payment_action",
}


def _judge_mode(state: ClaimGraphState) -> str:
    if state.risk_score >= settings.llm_judge_blocking_min_risk_score or state.risk_level == "HIGH":
        return "blocking"
    return "advisory"


def _claim_snapshot(state: ClaimGraphState) -> dict[str, Any]:
    return {
        "claim_id": state.claim_id,
        "risk_score": state.risk_score,
        "risk_level": state.risk_level,
        "errors": state.errors,
        "investigation_errors": state.investigation_errors,
        "tool_results": sorted(state.tool_results.keys()),
    }


def _load_prompts(state: ClaimGraphState, actions: list[str]) -> tuple[str, str]:
    system_artifact = load_prompt_artifact(domain="action_selection_judge", role="system", version="v1")
    user_artifact = load_prompt_artifact(domain="action_selection_judge", role="user", version="v1")
    user_prompt = render_prompt_template(
        user_artifact.body,
        {
            "claim_snapshot": json.dumps(_claim_snapshot(state), ensure_ascii=True),
            "investigation_findings": json.dumps(state.investigation_findings, ensure_ascii=True),
            "available_actions": json.dumps(AVAILABLE_ACTIONS, ensure_ascii=True),
            "selected_actions": json.dumps(actions, ensure_ascii=True),
        },
    )
    return system_artifact.body, user_prompt


def _append_action_tool(tool_calls: list[dict[str, Any]], action_name: str) -> None:
    tool_name = ACTION_TOOL_MAP[action_name]
    reason_map = {
        NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value: "LLM judge requested human review.",
        NextWorkflowAction.REQUEST_MORE_INFO.value: "LLM judge requested more information.",
        NextWorkflowAction.BLOCK_RECOMMENDED.value: "LLM judge recommended blocking the claim.",
        NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value: "LLM judge approved proceeding to payment guardrails.",
    }
    tool_calls.append(
        {
            "name": tool_name,
            "args": {
                "reason": reason_map[action_name],
                "priority": 85,
                "confidence": 0.8,
            },
            "id": f"judge-{tool_name}",
            "type": "tool_call",
        }
    )


async def judge_recommended_action(state: ClaimGraphState, llm_client: LLMClient | None = None) -> dict[str, Any]:
    notes = list(state.notes)
    if not state.messages or not isinstance(state.messages[-1], AIMessage):
        return {
            "action_selection_judgment": {
                "approved": True,
                "mode": _judge_mode(state),
                "rationale": "No action plan to review.",
                "missing_actions": [],
                "unnecessary_actions": [],
            },
            "notes": notes,
        }

    tool_calls = list(state.messages[-1].tool_calls or [])
    selected_actions = [
        action_name
        for action_name, tool_name in ACTION_TOOL_MAP.items()
        if any(tool_call["name"] == tool_name for tool_call in tool_calls)
    ]
    mode = _judge_mode(state)

    if not settings.enable_llm_action_judge and llm_client is None:
        notes.append(f"Action judge is disabled; proceeding in {mode} mode without LLM review.")
        return {
            "action_selection_judgment": {
                "approved": True,
                "mode": mode,
                "rationale": "LLM action judge disabled.",
                "missing_actions": [],
                "unnecessary_actions": [],
            },
            "notes": notes,
        }

    client = llm_client or LLMClient()
    system_prompt, user_prompt = _load_prompts(state, selected_actions)
    try:
        judgment = client.create_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=settings.llm_judge_model,
        )
    except Exception as exc:
        notes.append("Action judge failed; proceeding with deterministic action plan.")
        return {
            "action_selection_judgment": {
                "approved": True,
                "mode": mode,
                "rationale": f"Judge fallback due to error: {exc}",
                "missing_actions": [],
                "unnecessary_actions": [],
            },
            "notes": notes,
        }

    missing_actions = [name for name in judgment.get("missing_actions", []) if name in AVAILABLE_ACTIONS]
    unnecessary_actions = {name for name in judgment.get("unnecessary_actions", []) if name in AVAILABLE_ACTIONS}
    revised_tool_calls = list(tool_calls)
    applied = mode == "blocking"

    if applied:
        revised_tool_calls = [
            tool_call
            for tool_call in revised_tool_calls
            if all(tool_call["name"] != ACTION_TOOL_MAP[action] for action in unnecessary_actions)
        ]
        existing_actions = {
            action_name
            for action_name, tool_name in ACTION_TOOL_MAP.items()
            if any(tool_call["name"] == tool_name for tool_call in revised_tool_calls)
        }
        for action_name in missing_actions:
            if action_name in existing_actions:
                continue
            _append_action_tool(revised_tool_calls, action_name)
    notes.append(
        f"Action judge {'applied' if applied else 'recorded'} verdict in {mode} mode."
    )
    return {
        "action_selection_judgment": {
            "approved": bool(judgment.get("approved", True)),
            "mode": mode,
            "rationale": judgment.get("rationale", ""),
            "missing_actions": missing_actions,
            "unnecessary_actions": sorted(unnecessary_actions),
            "applied": applied,
        },
        "notes": notes,
        "messages": [AIMessage(content=state.messages[-1].content, tool_calls=revised_tool_calls)],
    }
