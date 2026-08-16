from __future__ import annotations

import json

from langchain_core.tools import tool

from app.enums import NextWorkflowAction


def _json(data: dict) -> str:
    return json.dumps(data, default=str)


@tool
async def recommend_human_review_action(reason: str, priority: int = 100, confidence: float = 0.95) -> str:
    """Recommend routing the claim to a human review task."""
    return _json(
        {
            "action": NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value,
            "reason": reason,
            "priority": priority,
            "confidence": confidence,
            "recommended": True,
        }
    )


@tool
async def recommend_request_more_info_action(reason: str, priority: int = 90, confidence: float = 0.9) -> str:
    """Recommend requesting more information from the claimant or operator."""
    return _json(
        {
            "action": NextWorkflowAction.REQUEST_MORE_INFO.value,
            "reason": reason,
            "priority": priority,
            "confidence": confidence,
            "recommended": True,
        }
    )


@tool
async def recommend_block_claim_action(reason: str, priority: int = 80, confidence: float = 0.88) -> str:
    """Recommend blocking the claim due to significant concerns in investigation results."""
    return _json(
        {
            "action": NextWorkflowAction.BLOCK_RECOMMENDED.value,
            "reason": reason,
            "priority": priority,
            "confidence": confidence,
            "recommended": True,
        }
    )


@tool
async def recommend_proceed_to_payment_action(reason: str, priority: int = 70, confidence: float = 0.82) -> str:
    """Recommend proceeding beyond investigation toward payment guardrails."""
    return _json(
        {
            "action": NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value,
            "reason": reason,
            "priority": priority,
            "confidence": confidence,
            "recommended": True,
        }
    )
