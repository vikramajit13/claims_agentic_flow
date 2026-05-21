from app.models.claims_workflow_state import ClaimreviewState
from app.nodes.analyse_evidence_node import analyse_evidence_node
from app.nodes.analyse_risk_node import analyse_risk_node
from app.nodes.generate_briefing_node import generate_briefing_node

try:
    from langgraph.graph import StateGraph
    from langgraph.graph.state import CompiledStateGraph
except ModuleNotFoundError:  # pragma: no cover
    StateGraph = None
    CompiledStateGraph = object


class _FallbackCompiledGraph:
    def invoke(self, state):
        graph_state = state if isinstance(state, ClaimreviewState) else ClaimreviewState(**state)
        for node in (analyse_evidence_node, analyse_risk_node, generate_briefing_node):
            updates = node(graph_state)
            graph_state = graph_state.copy(update=updates)
        return graph_state.dict()


def create_claims_processing_state_graph() -> CompiledStateGraph:
    if StateGraph is None:
        return _FallbackCompiledGraph()
    claims_graph = StateGraph(ClaimreviewState)
    claims_graph.add_node("evidence_analysis", analyse_evidence_node)
    claims_graph.add_node("risk_analysis", analyse_risk_node)
    claims_graph.add_node("generate_briefing", generate_briefing_node)
    claims_graph.add_edge("evidence_analysis", "risk_analysis")
    claims_graph.add_edge("risk_analysis", "generate_briefing")
    claims_graph.set_entry_point("evidence_analysis")
    claims_graph.set_finish_point("generate_briefing")
    return claims_graph.compile()


claims_review_graph = create_claims_processing_state_graph()
