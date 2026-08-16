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
from app.nodes.select_investigation_graph import select_investigation_graph
from app.nodes.start_claim import process_claim
from app.nodes.validate_claim_context import validate_claim_context
from app.tools import SAFE_READ_ONLY_TOOLS, get_tools_for_graph


class GraphBuilder(Protocol):
    def build(self) -> StateGraph: ...


@dataclass(frozen=True)
class GraphDefinition:
    name: str
    version: str
    builder_factory: type[GraphBuilder]


class BaseToolGraphBuilder:
    tool_graph_name: str = "investigate_claim_graph"

    def build(self) -> StateGraph:
        workflow = StateGraph(ClaimGraphState)
        workflow.add_node("claim_investigation_agent", claim_investigation_agent)
        available_tools = get_tools_for_graph(self.tool_graph_name) or SAFE_READ_ONLY_TOOLS
        workflow.add_node("read_only_tools", ToolNode(list(available_tools.values())))
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


class InvestigationGraphBuilder(BaseToolGraphBuilder):
    tool_graph_name = "investigate_claim_graph"


class CustomerHistoryGraphBuilder(BaseToolGraphBuilder):
    tool_graph_name = "customer_history_graph"


class DocumentEvidenceGraphBuilder(BaseToolGraphBuilder):
    tool_graph_name = "document_evidence_graph"

class ClaimReviewGraphBuilder:
    def build(self) -> StateGraph:
        workflow = StateGraph(ClaimGraphState)
        investigation_subgraph = InvestigationGraphBuilder().build().compile()
        customer_history_subgraph = CustomerHistoryGraphBuilder().build().compile()
        document_evidence_subgraph = DocumentEvidenceGraphBuilder().build().compile()
        workflow.add_node("process_claim", process_claim)
        workflow.add_node("validate_claim_context", validate_claim_context)
        workflow.add_node("analyse_risk", analyse_risk)
        workflow.add_node("select_investigation_graph", select_investigation_graph)
        workflow.add_node("claim_investigation", investigation_subgraph)
        workflow.add_node("customer_history_investigation", customer_history_subgraph)
        workflow.add_node("document_evidence_investigation", document_evidence_subgraph)
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
        workflow.add_edge("analyse_risk", "select_investigation_graph")
        workflow.add_conditional_edges(
            "select_investigation_graph",
            self._route_investigation_graph,
            {
                "claim_investigation": "claim_investigation",
                "customer_history_investigation": "customer_history_investigation",
                "document_evidence_investigation": "document_evidence_investigation",
            },
        )
        workflow.add_edge("claim_investigation", "recommend_next_action")
        workflow.add_edge("customer_history_investigation", "recommend_next_action")
        workflow.add_edge("document_evidence_investigation", "recommend_next_action")
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
    def _route_investigation_graph(state: ClaimGraphState) -> str:
        selected_graph = state.selected_investigation_graph or "investigate_claim_graph"
        if selected_graph == "customer_history_graph":
            return "customer_history_investigation"
        if selected_graph == "document_evidence_graph":
            return "document_evidence_investigation"
        return "claim_investigation"

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

CUSTOMER_HISTORY_GRAPH = GraphDefinition(
    name="customer_history_graph",
    version="v1",
    builder_factory=CustomerHistoryGraphBuilder,
)

DOCUMENT_EVIDENCE_GRAPH = GraphDefinition(
    name="document_evidence_graph",
    version="v1",
    builder_factory=DocumentEvidenceGraphBuilder,
)
