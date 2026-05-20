from app.models.claims_workflow_state import ClaimreviewState
from app.nodes.analyse_evidence_node import analyse_evidence_node

try:
    from langgraph.graph import StateGraph
    from langgraph.graph.state import CompiledStateGraph
except ModuleNotFoundError:  # pragma: no cover
    StateGraph = None
    CompiledStateGraph = object


class _FallbackCompiledGraph:
    def invoke(self, state):
        graph_state = state if isinstance(state, ClaimreviewState) else ClaimreviewState(**state)
        updates = analyse_evidence_node(graph_state)
        return graph_state.copy(update=updates).dict()


def create_claims_processing_state_graph() -> CompiledStateGraph:
    if StateGraph is None:
        return _FallbackCompiledGraph()
    claims_graph = StateGraph(ClaimreviewState)
    claims_graph.add_node("evidence_analysis", analyse_evidence_node)
    claims_graph.set_entry_point("evidence_analysis")
    claims_graph.set_finish_point("evidence_analysis")
    return claims_graph.compile()


claims_review_graph = create_claims_processing_state_graph()
