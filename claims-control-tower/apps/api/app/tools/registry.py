from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from app.graph.state import ClaimGraphState
from app.tools.read_only_claim_tools import (
    get_claim_history,
    get_claim_timeline,
    get_customer_risk_overview,
    get_document_metadata,
    get_document_text_evidence,
    get_guardrail_results,
    get_policy_coverage_summary,
    get_prior_rejection_details,
)

ToolCondition = Callable[[ClaimGraphState, set[str]], bool]
ToolArgsBuilder = Callable[[ClaimGraphState], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    tool: Any
    description: str
    graphs: tuple[str, ...]
    condition: ToolCondition
    args_builder: ToolArgsBuilder


def _not_seen(tool_name: str) -> ToolCondition:
    return lambda _state, seen: tool_name not in seen


def _has_customer_and_not_seen(tool_name: str) -> ToolCondition:
    return lambda state, seen: state.customer_id is not None and tool_name not in seen


def _has_policy_and_not_seen(tool_name: str) -> ToolCondition:
    return lambda state, seen: bool(state.policy_id) and tool_name not in seen


def _has_documents_and_not_seen(tool_name: str) -> ToolCondition:
    return lambda state, seen: bool(state.claim_documents) and tool_name not in seen


GRAPH_TOOL_DESCRIPTIONS: dict[str, str] = {
    "claim_review_graph": "Full review graph for validation, risk analysis, investigation, and next action.",
    "investigate_claim_graph": "Standalone investigation graph for broad read-only claim evidence gathering.",
    "customer_history_graph": "Customer-history-focused graph for prior claims, rejections, and exposure patterns.",
    "document_evidence_graph": "Document-evidence-focused graph for OCR text, metadata, and timeline inspection.",
}


GRAPH_SELECTION_CATALOG: dict[str, str] = {
    "investigate_claim_graph": "Use when the claim needs broad claim, policy, document, and guardrail context.",
    "customer_history_graph": "Use when customer behavior, prior rejections, or repeat-claim patterns matter most.",
    "document_evidence_graph": "Use when OCR text, extraction quality, or document sequencing should drive the investigation.",
}


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="get_claim_history",
        tool=get_claim_history,
        description="Prior claims for the customer inside a lookback window.",
        graphs=("claim_review_graph", "investigate_claim_graph", "customer_history_graph"),
        condition=_has_customer_and_not_seen("get_claim_history"),
        args_builder=lambda state: {
            "customer_id": state.customer_id,
            "lookback_months": 12,
            "exclude_claim_id": state.claim_id,
        },
    ),
    ToolDefinition(
        name="get_prior_rejection_details",
        tool=get_prior_rejection_details,
        description="Rejected customer claims that may justify escalation or blocking.",
        graphs=("claim_review_graph", "investigate_claim_graph", "customer_history_graph"),
        condition=_has_customer_and_not_seen("get_prior_rejection_details"),
        args_builder=lambda state: {
            "customer_id": state.customer_id,
            "exclude_claim_id": state.claim_id,
        },
    ),
    ToolDefinition(
        name="get_customer_risk_overview",
        tool=get_customer_risk_overview,
        description="Customer-level aggregate claim history and exposure summary.",
        graphs=("claim_review_graph", "investigate_claim_graph", "customer_history_graph"),
        condition=_has_customer_and_not_seen("get_customer_risk_overview"),
        args_builder=lambda state: {
            "customer_id": state.customer_id,
            "exclude_claim_id": state.claim_id,
        },
    ),
    ToolDefinition(
        name="get_policy_coverage_summary",
        tool=get_policy_coverage_summary,
        description="Policy limit, deductible, and claim-type coverage summary.",
        graphs=("claim_review_graph", "investigate_claim_graph"),
        condition=_has_policy_and_not_seen("get_policy_coverage_summary"),
        args_builder=lambda state: {"policy_id": state.policy_id},
    ),
    ToolDefinition(
        name="get_document_metadata",
        tool=get_document_metadata,
        description="Structured metadata for claim documents and extracted invoice fields.",
        graphs=("claim_review_graph", "investigate_claim_graph", "document_evidence_graph"),
        condition=_not_seen("get_document_metadata"),
        args_builder=lambda state: {"claim_id": state.claim_id},
    ),
    ToolDefinition(
        name="get_document_text_evidence",
        tool=get_document_text_evidence,
        description="Compact OCR and normalized-text snippets for the most relevant documents.",
        graphs=("claim_review_graph", "investigate_claim_graph", "document_evidence_graph"),
        condition=_has_documents_and_not_seen("get_document_text_evidence"),
        args_builder=lambda state: {"claim_id": state.claim_id, "max_documents": 3},
    ),
    ToolDefinition(
        name="get_claim_timeline",
        tool=get_claim_timeline,
        description="Timeline of claim creation, document processing, and workflow events.",
        graphs=("claim_review_graph", "investigate_claim_graph", "customer_history_graph", "document_evidence_graph"),
        condition=_not_seen("get_claim_timeline"),
        args_builder=lambda state: {"claim_id": state.claim_id},
    ),
    ToolDefinition(
        name="get_guardrail_results",
        tool=get_guardrail_results,
        description="Deterministic guardrail decisions for pre-adjudication review.",
        graphs=("claim_review_graph", "investigate_claim_graph", "document_evidence_graph"),
        condition=_not_seen("get_guardrail_results"),
        args_builder=lambda state: {
            "claim_id": state.claim_id,
            "workflow_run_id": state.graph_run_id,
            "phase": "PRE_ADJUDICATION",
        },
    ),
)


SAFE_READ_ONLY_TOOLS = {definition.name: definition.tool for definition in TOOL_DEFINITIONS}


def list_tool_catalog(graph_name: str) -> list[dict[str, str]]:
    return [
        {"name": definition.name, "description": definition.description}
        for definition in TOOL_DEFINITIONS
        if graph_name in definition.graphs
    ]


def list_graph_catalog() -> list[dict[str, str]]:
    return [{"graph_name": key, "description": description} for key, description in GRAPH_TOOL_DESCRIPTIONS.items()]


def list_investigation_graph_options() -> list[dict[str, str]]:
    return [{"graph_name": key, "description": description} for key, description in GRAPH_SELECTION_CATALOG.items()]


def get_tools_for_graph(graph_name: str) -> dict[str, Any]:
    return {
        definition.name: definition.tool
        for definition in TOOL_DEFINITIONS
        if graph_name in definition.graphs
    }


def build_tool_calls_for_graph(state: ClaimGraphState, graph_name: str) -> list[dict[str, Any]]:
    existing_results = set(state.tool_results.keys())
    tool_calls: list[dict[str, Any]] = []

    for definition in TOOL_DEFINITIONS:
        if graph_name not in definition.graphs:
            continue
        if not definition.condition(state, existing_results):
            continue
        tool_calls.append(
            {
                "name": definition.name,
                "args": definition.args_builder(state),
                "id": f"tool-{uuid4()}",
                "type": "tool_call",
            }
        )

    return tool_calls
