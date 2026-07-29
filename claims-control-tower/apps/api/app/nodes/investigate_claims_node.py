from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import ClaimGraphState


def build_investigation_tool_calls(state: ClaimGraphState) -> list[dict[str, Any]]:
    existing_results = set(state.tool_results.keys())
    tool_calls: list[dict[str, Any]] = []

    if state.customer_id is not None and "get_claim_history" not in existing_results:
        tool_calls.append(
            {
                "name": "get_claim_history",
                "args": {
                    "customer_id": state.customer_id,
                    "lookback_months": 12,
                    "exclude_claim_id": state.claim_id,
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    if state.customer_id is not None and "get_prior_rejection_details" not in existing_results:
        tool_calls.append(
            {
                "name": "get_prior_rejection_details",
                "args": {
                    "customer_id": state.customer_id,
                    "exclude_claim_id": state.claim_id,
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    if state.policy_id and "get_policy_coverage_summary" not in existing_results:
        tool_calls.append(
            {
                "name": "get_policy_coverage_summary",
                "args": {"policy_id": state.policy_id},
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    if "get_document_metadata" not in existing_results:
        tool_calls.append(
            {
                "name": "get_document_metadata",
                "args": {"claim_id": state.claim_id},
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    if "get_guardrail_results" not in existing_results:
        tool_calls.append(
            {
                "name": "get_guardrail_results",
                "args": {
                    "claim_id": state.claim_id,
                    "workflow_run_id": state.graph_run_id,
                    "phase": "PRE_ADJUDICATION",
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    return tool_calls


def claim_investigation_agent(state: ClaimGraphState) -> dict[str, Any]:
    tool_calls = build_investigation_tool_calls(state)
    notes = list(state.investigation_notes)

    if not tool_calls:
        notes.append("No additional read-only investigation tools were required.")
        return {
            "current_step": "claim_investigation",
            "investigation_required": False,
            "investigation_notes": notes,
            "completed_steps": [*state.completed_steps, "claim_investigation"],
        }

    notes.append(f"Investigation agent selected {len(tool_calls)} read-only tool call(s).")
    return {
        "current_step": "claim_investigation",
        "investigation_required": True,
        "investigation_notes": notes,
        "completed_steps": [*state.completed_steps, "claim_investigation"],
        "messages": [AIMessage(content="Investigating claim context with read-only tools.", tool_calls=tool_calls)],
    }


def merge_investigation_tool_results(state: ClaimGraphState) -> dict[str, Any]:
    tool_results = dict(state.tool_results)
    notes = list(state.investigation_notes)
    errors = list(state.investigation_errors)

    for message in state.messages:
        if not isinstance(message, ToolMessage):
            continue
        if message.name in tool_results:
            continue

        try:
            parsed = json.loads(message.content)
        except json.JSONDecodeError:
            parsed = {"raw_content": message.content}
            errors.append(f"tool_result_parse_failed:{message.name}")

        tool_results[message.name] = parsed
        notes.append(f"Captured tool result from {message.name}.")

    return {
        "current_step": "claim_investigation_merged",
        "tool_results": tool_results,
        "investigation_notes": notes,
        "investigation_errors": errors,
        "completed_steps": [*state.completed_steps, "claim_investigation_merged"],
    }
