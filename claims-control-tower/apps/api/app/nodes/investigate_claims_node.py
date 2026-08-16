from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import ClaimGraphState
from app.tools import build_tool_calls_for_graph, list_graph_catalog, list_tool_catalog


GRAPH_TOOL_FALLBACK = "investigate_claim_graph"


def build_investigation_tool_calls(state: ClaimGraphState) -> list[dict[str, Any]]:
    graph_name = state.selected_investigation_graph or state.graph_name or GRAPH_TOOL_FALLBACK
    return build_tool_calls_for_graph(state, graph_name)


def claim_investigation_agent(state: ClaimGraphState) -> dict[str, Any]:
    tool_calls = build_investigation_tool_calls(state)
    notes = list(state.investigation_notes)
    graph_name = state.selected_investigation_graph or state.graph_name or GRAPH_TOOL_FALLBACK
    tool_catalog = list_tool_catalog(graph_name)
    graph_catalog = list_graph_catalog()

    if not tool_calls:
        notes.append("No additional read-only investigation tools were required.")
        return {
            "current_step": "claim_investigation",
            "investigation_required": False,
            "investigation_notes": notes,
            "tool_catalog": tool_catalog,
            "graph_catalog": graph_catalog,
            "completed_steps": [*state.completed_steps, "claim_investigation"],
        }

    notes.append(f"Investigation agent selected {len(tool_calls)} read-only tool call(s) for {graph_name}.")
    return {
        "current_step": "claim_investigation",
        "investigation_required": True,
        "investigation_notes": notes,
        "tool_catalog": tool_catalog,
        "graph_catalog": graph_catalog,
        "completed_steps": [*state.completed_steps, "claim_investigation"],
        "messages": [AIMessage(content="Investigating claim context with read-only tools.", tool_calls=tool_calls)],
    }


def merge_investigation_tool_results(state: ClaimGraphState) -> dict[str, Any]:
    tool_results = dict(state.tool_results)
    notes = list(state.investigation_notes)
    errors = list(state.investigation_errors)
    findings = list(state.investigation_findings)

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
        if isinstance(parsed, dict):
            if message.name == "get_guardrail_results" and parsed.get("overall_decision"):
                findings.append(f"Guardrail decision: {parsed['overall_decision']}")
            if message.name == "get_policy_coverage_summary" and parsed.get("status"):
                findings.append(f"Policy status: {parsed['status']}")
            if message.name == "get_prior_rejection_details":
                findings.append(f"Prior rejections found: {parsed.get('prior_rejection_count', 0)}")
            if message.name == "get_customer_risk_overview":
                findings.append(f"Customer claim count: {parsed.get('claim_count', 0)}")

    return {
        "current_step": "claim_investigation_merged",
        "tool_results": tool_results,
        "investigation_notes": notes,
        "investigation_errors": errors,
        "investigation_findings": findings,
        "completed_steps": [*state.completed_steps, "claim_investigation_merged"],
    }
