from app.models.claims_workflow_state import ClaimreviewState
from app.nodes.agent_decide_tool_node import agent_decide_tool_node
from app.nodes.analyse_evidence_node import analyse_evidence_node
from app.nodes.analyse_risk_node import analyse_risk_node
from app.nodes.execute_tool_node import execute_tool_node
from app.nodes.generate_briefing_node import generate_briefing_node
from app.nodes.identify_information_gaps_node import identify_information_gaps_node
from app.nodes.merge_tool_result_node import merge_tool_result_node
from app.nodes.route_next_action_node import route_next_action_node

try:
    from langgraph.graph import StateGraph
    from langgraph.graph.state import CompiledStateGraph
except ModuleNotFoundError:  # pragma: no cover
    StateGraph = None
    CompiledStateGraph = object


class _FallbackCompiledGraph:
    def invoke(self, state):
        graph_state = (
            state if isinstance(state, ClaimreviewState) else ClaimreviewState(**state)
        )
        for node in (analyse_evidence_node, analyse_risk_node):
            updates = node(graph_state)
            graph_state = graph_state.copy(update=updates)
        max_iterations = 3
        for _ in range(max_iterations):
            updates = identify_information_gaps_node(graph_state)
            graph_state = graph_state.copy(update=updates)
            if not graph_state.investigation_required:
                break
            updates = agent_decide_tool_node(graph_state)
            graph_state = graph_state.copy(update=updates)
            selected_tool = graph_state.selected_tool_decision
            if isinstance(selected_tool, dict):
                selected_tool = selected_tool.get("selected_tool")
            elif selected_tool is not None:
                selected_tool = selected_tool.selected_tool
            if not selected_tool:
                break
            updates = execute_tool_node(graph_state)
            graph_state = graph_state.copy(update=updates)
            updates = merge_tool_result_node(graph_state)
            graph_state = graph_state.copy(update=updates)
        for node in (generate_briefing_node, route_next_action_node):
            updates = node(graph_state)
            graph_state = graph_state.copy(update=updates)
        return graph_state.dict()


def _route_after_information_gap_analysis(state: ClaimreviewState) -> str:
    return "agent_decide_tool" if state.investigation_required else "generate_briefing"


def _route_after_tool_decision(state: ClaimreviewState) -> str:
    decision = state.selected_tool_decision
    if decision is None:
        return "generate_briefing"
    selected_tool = decision.get("selected_tool") if isinstance(decision, dict) else decision.selected_tool
    return "execute_tool" if selected_tool else "generate_briefing"


def create_claims_processing_state_graph() -> CompiledStateGraph:
    if StateGraph is None:
        return _FallbackCompiledGraph()
    claims_graph = StateGraph(ClaimreviewState)
    claims_graph.add_node("evidence_analysis", analyse_evidence_node)
    claims_graph.add_node("risk_analysis", analyse_risk_node)
    claims_graph.add_node("identify_information_gaps", identify_information_gaps_node)
    claims_graph.add_node("agent_decide_tool", agent_decide_tool_node)
    claims_graph.add_node("execute_tool", execute_tool_node)
    claims_graph.add_node("merge_tool_result", merge_tool_result_node)
    claims_graph.add_node("generate_briefing", generate_briefing_node)
    claims_graph.add_node("route_next_action", route_next_action_node)
    claims_graph.add_edge("evidence_analysis", "risk_analysis")
    claims_graph.add_edge("risk_analysis", "identify_information_gaps")
    claims_graph.add_conditional_edges(
        "identify_information_gaps",
        _route_after_information_gap_analysis,
        {
            "agent_decide_tool": "agent_decide_tool",
            "generate_briefing": "generate_briefing",
        },
    )
    claims_graph.add_conditional_edges(
        "agent_decide_tool",
        _route_after_tool_decision,
        {
            "execute_tool": "execute_tool",
            "generate_briefing": "generate_briefing",
        },
    )
    claims_graph.add_edge("execute_tool", "merge_tool_result")
    claims_graph.add_edge("merge_tool_result", "identify_information_gaps")
    claims_graph.add_edge("generate_briefing", "route_next_action")
    claims_graph.set_entry_point("evidence_analysis")
    claims_graph.set_finish_point("route_next_action")
    return claims_graph.compile()


claims_review_graph = create_claims_processing_state_graph()
