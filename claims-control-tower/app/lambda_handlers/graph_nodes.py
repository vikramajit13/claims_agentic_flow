from __future__ import annotations

from app.agent.claims_review_graph import create_risk_investigation_node
from app.agent.risk.risk_agent_graph import risk_agent_graph
from app.models.claims_workflow_state import ClaimreviewState
from app.nodes.analyse_evidence_node import analyse_evidence_node
from app.nodes.generate_briefing_node import generate_briefing_node
from app.nodes.route_next_action_node import route_next_action_node


def analyse_evidence_handler(event, context):
    state = ClaimreviewState(**event)
    return analyse_evidence_node(state)


def risk_investigation_handler(event, context):
    state = ClaimreviewState(**event)
    node = create_risk_investigation_node(risk_agent_graph)
    return node(state)


def generate_briefing_handler(event, context):
    state = ClaimreviewState(**event)
    return generate_briefing_node(state)


def route_next_action_handler(event, context):
    state = ClaimreviewState(**event)
    return route_next_action_node(state)

