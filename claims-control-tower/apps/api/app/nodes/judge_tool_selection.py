from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage

from app.config import settings
from app.graph.state import ClaimGraphState
from app.llm_client import LLMClient
from app.prompt_loader import load_prompt_artifact, render_prompt_template
from app.tools import build_named_tool_call, list_tool_catalog


def _judge_mode(state: ClaimGraphState) -> str:
    if state.risk_score >= settings.llm_judge_blocking_min_risk_score or state.risk_level == "HIGH":
        return "blocking"
    return "advisory"


def _claim_snapshot(state: ClaimGraphState) -> dict[str, Any]:
    return {
        "claim_id": state.claim_id,
        "customer_id": state.customer_id,
        "policy_id": state.policy_id,
        "claim_type": state.claim_type,
        "claim_amount": state.claim_amount,
        "risk_score": state.risk_score,
        "risk_level": state.risk_level,
        "document_count": len(state.claim_documents),
        "errors": state.errors,
    }


def _load_prompts(state: ClaimGraphState, tool_names: list[str], graph_name: str) -> tuple[str, str]:
    system_artifact = load_prompt_artifact(domain="tool_selection_judge", role="system", version="v1")
    user_artifact = load_prompt_artifact(domain="tool_selection_judge", role="user", version="v1")
    user_prompt = render_prompt_template(
        user_artifact.body,
        {
            "graph_name": graph_name,
            "selected_graph_reason": state.selected_investigation_reason or "",
            "claim_snapshot": json.dumps(_claim_snapshot(state), ensure_ascii=True),
            "investigation_plan": json.dumps(state.investigation_plan, ensure_ascii=True),
            "available_tools": json.dumps(list_tool_catalog(graph_name), ensure_ascii=True),
            "selected_tools": json.dumps(tool_names, ensure_ascii=True),
        },
    )
    return system_artifact.body, user_prompt


def _extract_last_tool_calls(state: ClaimGraphState) -> tuple[AIMessage | None, list[dict[str, Any]]]:
    if not state.messages:
        return None, []
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        return None, []
    tool_calls = list(getattr(last_message, "tool_calls", []) or [])
    return last_message, tool_calls


async def judge_tool_selection(state: ClaimGraphState, llm_client: LLMClient | None = None) -> dict[str, Any]:
    graph_name = state.selected_investigation_graph or state.graph_name or "investigate_claim_graph"
    notes = list(state.investigation_notes)
    mode = _judge_mode(state)
    last_message, tool_calls = _extract_last_tool_calls(state)
    if last_message is None or not tool_calls:
        return {
            "tool_selection_judgment": {
                "approved": True,
                "mode": mode,
                "rationale": "No planned tool calls required judgment.",
                "missing_tools": [],
                "unnecessary_tools": [],
            },
            "investigation_notes": [*notes, "Tool-selection judge skipped because no tool calls were planned."],
        }

    if not settings.enable_llm_tool_selection_judge and llm_client is None:
        return {
            "tool_selection_judgment": {
                "approved": True,
                "mode": mode,
                "rationale": "LLM judge disabled.",
                "missing_tools": [],
                "unnecessary_tools": [],
            },
            "investigation_notes": [*notes, f"Tool-selection judge is disabled; proceeding in {mode} mode without LLM review."],
        }

    client = llm_client or LLMClient()
    selected_tool_names = [tool_call["name"] for tool_call in tool_calls]
    system_prompt, user_prompt = _load_prompts(state, selected_tool_names, graph_name)

    try:
        judgment = client.judge_tool_selection(system_prompt=system_prompt, user_prompt=user_prompt)
    except Exception as exc:
        return {
            "tool_selection_judgment": {
                "approved": True,
                "mode": mode,
                "rationale": f"Judge fallback due to error: {exc}",
                "missing_tools": [],
                "unnecessary_tools": [],
            },
            "investigation_notes": [*notes, "Tool-selection judge failed; proceeding with deterministic tool plan."],
        }

    approved = bool(judgment.get("approved", True))
    missing_tools = [name for name in judgment.get("missing_tools", []) if isinstance(name, str)]
    unnecessary_tools = {name for name in judgment.get("unnecessary_tools", []) if isinstance(name, str)}

    applied = mode == "blocking"
    revised_tool_calls = list(tool_calls)
    if applied:
        revised_tool_calls = [tool_call for tool_call in tool_calls if tool_call["name"] not in unnecessary_tools]
    existing_tool_names = {tool_call["name"] for tool_call in revised_tool_calls}
    added_tools: list[str] = []
    if applied:
        for tool_name in missing_tools:
            if tool_name in existing_tool_names:
                continue
            tool_call = build_named_tool_call(state, graph_name, tool_name)
            if tool_call is None:
                continue
            revised_tool_calls.append(tool_call)
            existing_tool_names.add(tool_name)
            added_tools.append(tool_name)

    notes.append(
        f"Tool-selection judge {'approved' if approved else 'flagged'} the plan for {graph_name} in {mode} mode."
    )
    if added_tools:
        notes.append(f"Tool-selection judge added tool(s): {', '.join(added_tools)}.")

    return {
        "tool_selection_judgment": {
            "approved": approved,
            "mode": mode,
            "rationale": judgment.get("rationale", ""),
            "missing_tools": missing_tools,
            "unnecessary_tools": sorted(unnecessary_tools),
            "added_tools": added_tools,
            "applied": applied,
        },
        "investigation_notes": notes,
        "messages": [AIMessage(content=last_message.content, tool_calls=revised_tool_calls)],
    }
