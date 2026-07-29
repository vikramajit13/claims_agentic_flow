from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.enums import NextWorkflowAction
from app.graph.state import ClaimGraphState
from app.nodes.analyse_risk import analyse_risk
from app.nodes.human_review import human_in_the_loop_review
from app.nodes.investigate_claims_node import claim_investigation_agent, merge_investigation_tool_results
from app.nodes.post_human_review import post_human_review
from app.nodes.recommend_next_action import recommend_next_action
from app.nodes.start_claim import process_claim
from app.nodes.validate_claim_context import validate_claim_context
from app.tools import SAFE_READ_ONLY_TOOLS


class GraphBuilder(Protocol):
    def build(self) -> StateGraph: ...


@dataclass(frozen=True)
class GraphDefinition:
    name: str
    version: str
    builder_factory: type[GraphBuilder]


class InvestigationGraphBuilder:
    def build(self) -> StateGraph:
        workflow = StateGraph(ClaimGraphState)
        workflow.add_node("claim_investigation_agent", claim_investigation_agent)
        workflow.add_node("read_only_tools", ToolNode(list(SAFE_READ_ONLY_TOOLS.values())))
        workflow.add_node("merge_investigation_tool_results", merge_investigation_tool_results)

        workflow.add_edge(START, "claim_investigation_agent")
        workflow.add_conditional_edges(
            "claim_investigation_agent",
            self._route_after_agent,
            {
                "read_only_tools": "read_only_tools",
                "merge_investigation_tool_results": "merge_investigation_tool_results",
            },
        )
        workflow.add_edge("read_only_tools", "merge_investigation_tool_results")
        workflow.add_edge("merge_investigation_tool_results", END)
        return workflow

    @staticmethod
    def _route_after_agent(state: ClaimGraphState) -> str:
        if state.messages:
            last_message = state.messages[-1]
            if getattr(last_message, "tool_calls", None):
                return "read_only_tools"
        return "merge_investigation_tool_results"

class ClaimReviewGraphBuilder:
    def build(self) -> StateGraph:
        workflow = StateGraph(ClaimGraphState)
        investigation_subgraph = InvestigationGraphBuilder().build().compile()
        workflow.add_node("process_claim", process_claim)
        workflow.add_node("validate_claim_context", validate_claim_context)
        workflow.add_node("analyse_risk", analyse_risk)
        workflow.add_node("claim_investigation", investigation_subgraph)
        workflow.add_node("human_review", human_in_the_loop_review)
        workflow.add_node("post_human_review", post_human_review)
        workflow.add_node("recommend_next_action", recommend_next_action)

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
        workflow.add_edge("analyse_risk", "claim_investigation")
        workflow.add_edge("claim_investigation", "recommend_next_action")
        workflow.add_conditional_edges(
            "recommend_next_action",
            self._route_after_recommendation,
            {
                NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK.value: "human_review",
                NextWorkflowAction.REQUEST_MORE_INFO.value: END,
                NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value: END,
                NextWorkflowAction.BLOCK_RECOMMENDED.value: END,
            },
        )
        workflow.add_edge("post_human_review", END)
        return workflow

    @staticmethod
    def _route_after_validation(state: ClaimGraphState) -> str:
        if state.requires_human_review or state.hitl_required:
            return "human_review"
        return "analyse_risk"

    @staticmethod
    def _route_after_recommendation(state: ClaimGraphState) -> str:
        return state.recommended_next_action or NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS.value


CLAIM_REVIEW_GRAPH = GraphDefinition(
    name="claim_review_graph",
    version="v1",
    builder_factory=ClaimReviewGraphBuilder,
)

CLAIM_INVESTIGATION_GRAPH = GraphDefinition(
    name="investigate_claim_graph",
    version="v1",
    builder_factory=InvestigationGraphBuilder,
)
