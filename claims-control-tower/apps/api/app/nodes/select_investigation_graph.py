from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import ClaimGraphState
from app.tools import list_investigation_graph_options

DEFAULT_GRAPH = "investigate_claim_graph"


def _read_value(document: object, key: str):
    if isinstance(document, Mapping):
        return document.get(key)
    return getattr(document, key, None)


def _has_document_evidence(state: ClaimGraphState) -> bool:
    return any(
        bool(
            _read_value(document, "document_text")
            or _read_value(document, "normalized_document_type")
            or _read_value(document, "normalized_payload")
        )
        for document in state.claim_documents
    )


def _needs_guardrail_review(state: ClaimGraphState) -> bool:
    return bool((state.claim_amount or 0) > 5000 or any("invoice_after_incident" in error for error in state.errors))


def build_graph_selection_tool_calls(state: ClaimGraphState) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []

    if _has_document_evidence(state):
        tool_calls.append(
            {
                "name": "recommend_document_evidence_graph",
                "args": {
                    "reason": "OCR or normalized evidence is already available and should be inspected first.",
                    "priority": 100,
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )
    if _needs_guardrail_review(state):
        tool_calls.append(
            {
                "name": "recommend_guardrail_review_graph",
                "args": {
                    "reason": "Claim amount or date anomalies suggest deterministic guardrail review.",
                    "priority": 90,
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )
    if state.customer_id is not None and ((state.risk_level or "").upper() in {"HIGH", "CRITICAL"} or (state.risk_score or 0) >= 70):
        tool_calls.append(
            {
                "name": "recommend_customer_history_graph",
                "args": {
                    "reason": "Elevated risk and customer context make prior-claim history relevant.",
                    "priority": 80,
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )
    if state.policy_id:
        tool_calls.append(
            {
                "name": "recommend_policy_coverage_graph",
                "args": {
                    "reason": "Policy coverage and deductible validation can shape the final recommendation.",
                    "priority": 70,
                },
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    tool_calls.append(
        {
            "name": "recommend_broad_investigation_graph",
            "args": {
                "reason": "Fallback broad investigation remains available when no specialist is a stronger fit.",
                "priority": 10,
            },
            "id": f"tool-{uuid4()}",
            "type": "tool_call",
        }
    )
    return tool_calls


def select_investigation_graph(state: ClaimGraphState) -> dict[str, Any]:
    tool_calls = build_graph_selection_tool_calls(state)
    notes = list(state.investigation_notes)
    notes.append(f"Investigation selector prepared {len(tool_calls)} graph recommendation tool call(s).")
    return {
        "current_step": "select_investigation_graph",
        "graph_catalog": list_investigation_graph_options(),
        "investigation_notes": notes,
        "messages": [AIMessage(content="Selecting the best investigation graph.", tool_calls=tool_calls)],
    }


def merge_selected_investigation_graph(state: ClaimGraphState) -> dict[str, Any]:
    plan: list[dict[str, str]] = []
    notes = list(state.investigation_notes)
    selected_graph = DEFAULT_GRAPH
    selected_reason = "Fallback broad investigation remains available when no specialist is a stronger fit."
    best_priority = -1

    for message in state.messages:
        if not isinstance(message, ToolMessage):
            continue

        try:
            parsed = json.loads(message.content)
        except json.JSONDecodeError:
            notes.append(f"Graph recommendation parse failed for {message.name}.")
            continue

        graph_name = str(parsed.get("graph_name") or DEFAULT_GRAPH)
        reason = str(parsed.get("reason") or "")
        priority = int(parsed.get("priority") or 0)
        if graph_name not in {item["graph_name"] for item in plan}:
            plan.append({"graph_name": graph_name, "reason": reason})
        if parsed.get("recommended") and priority > best_priority:
            selected_graph = graph_name
            selected_reason = reason
            best_priority = priority

    notes.append(f"Investigation graph selected: {selected_graph}. {selected_reason}")
    return {
        "current_step": "select_investigation_graph_merged",
        "selected_investigation_graph": selected_graph,
        "selected_investigation_reason": selected_reason,
        "investigation_plan": plan,
        "investigation_notes": notes,
    }
