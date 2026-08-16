from __future__ import annotations

import json

from langchain_core.tools import tool


def _json(data: dict) -> str:
    return json.dumps(data, default=str)


@tool
async def recommend_document_evidence_graph(reason: str, priority: int = 100) -> str:
    """Recommend the document-evidence investigation graph when OCR or normalized text should drive the workflow."""
    return _json(
        {
            "graph_name": "document_evidence_graph",
            "reason": reason,
            "priority": priority,
            "recommended": True,
        }
    )


@tool
async def recommend_guardrail_review_graph(reason: str, priority: int = 90) -> str:
    """Recommend the guardrail-review investigation graph when deterministic policy or invoice checks should lead."""
    return _json(
        {
            "graph_name": "guardrail_review_graph",
            "reason": reason,
            "priority": priority,
            "recommended": True,
        }
    )


@tool
async def recommend_customer_history_graph(reason: str, priority: int = 80) -> str:
    """Recommend the customer-history investigation graph when prior claims or rejections are the best next branch."""
    return _json(
        {
            "graph_name": "customer_history_graph",
            "reason": reason,
            "priority": priority,
            "recommended": True,
        }
    )


@tool
async def recommend_policy_coverage_graph(reason: str, priority: int = 70) -> str:
    """Recommend the policy-coverage investigation graph when coverage, deductible, or claim-type alignment matters."""
    return _json(
        {
            "graph_name": "policy_coverage_graph",
            "reason": reason,
            "priority": priority,
            "recommended": True,
        }
    )


@tool
async def recommend_broad_investigation_graph(reason: str, priority: int = 10) -> str:
    """Recommend the broad investigation graph as a fallback when no specialist graph is a stronger fit."""
    return _json(
        {
            "graph_name": "investigate_claim_graph",
            "reason": reason,
            "priority": priority,
            "recommended": True,
        }
    )
