from app.models.claims_workflow_state import ClaimreviewState
from app.nodes.analyse_evidence_node import analyse_evidence_node
from app.nodes.generate_briefing_node import generate_briefing_node
from app.nodes.route_next_action_node import route_next_action_node
from app.agent.claims_review_graph import create_risk_investigation_node
from app.agent.risk.risk_agent_graph import risk_agent_graph
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph


def create_claims_processing_state_graph() -> CompiledStateGraph:
    claims_graph = StateGraph(ClaimreviewState)
    claims_graph.add_node("analyse_evidence", analyse_evidence_node)
    claims_graph.add_node("risk_investigation", create_risk_investigation_node(risk_agent_graph))
    claims_graph.add_node("generate_briefing", generate_briefing_node)
    claims_graph.add_node("route_next_action", route_next_action_node)
    claims_graph.add_edge("analyse_evidence", "risk_investigation")
    claims_graph.add_edge("risk_investigation", "generate_briefing")
    claims_graph.add_edge("generate_briefing", "route_next_action")
    claims_graph.set_entry_point("analyse_evidence")
    claims_graph.set_finish_point("route_next_action")
    return claims_graph.compile()


claims_review_graph = create_claims_processing_state_graph()
