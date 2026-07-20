from __future__ import annotations

from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from app.graph.state import ClaimGraphState
from app.nodes.analyse_risk import analyse_risk
from app.nodes.human_review import human_in_the_loop_review
from app.nodes.start_claim import process_claim
from app.nodes.validate_claim_context import validate_claim_context


@dataclass(frozen=True)
class GraphDefinition:
    name: str
    version: str
    builder: StateGraph


class ClaimReviewGraphBuilder:
    def build(self) -> StateGraph:
        workflow = StateGraph(ClaimGraphState)
        workflow.add_node("process_claim", process_claim)
        workflow.add_node("validate_claim_context", validate_claim_context)
        workflow.add_node("analyse_risk", analyse_risk)
        workflow.add_node("human_review", human_in_the_loop_review)

        workflow.add_edge(START, "process_claim")
        workflow.add_edge("process_claim", "validate_claim_context")
        workflow.add_conditional_edges(
            "validate_claim_context",
            self._route_after_validation,
            {
                "human_review": "human_review",
                "analyse_risk": "analyse_risk",
            },
        )
        workflow.add_conditional_edges(
            "analyse_risk",
            self._route_after_risk,
            {
                "human_review": "human_review",
                "complete": END,
            },
        )
        workflow.add_edge("human_review", END)
        return workflow

    @staticmethod
    def _route_after_validation(state: ClaimGraphState) -> str:
        if state.requires_human_review or state.hitl_required:
            return "human_review"
        return "analyse_risk"

    @staticmethod
    def _route_after_risk(state: ClaimGraphState) -> str:
        if state.requires_human_review or state.hitl_required:
            return "human_review"
        return "complete"
