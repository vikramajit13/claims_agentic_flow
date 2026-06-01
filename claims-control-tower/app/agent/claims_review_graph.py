# app/graphs/claims_review_graph.py

from langchain.messages import HumanMessage
from app.models.claims_workflow_state import ClaimreviewState


def create_risk_investigation_node(risk_agent_graph):

    def risk_investigation_node(state: ClaimreviewState):
        result = risk_agent_graph.invoke(
            {
                "case_packet": state.case_packet,
                "messages": [
                    HumanMessage(
                        content=(
                            "Investigate risk for this claim. "
                            "Use approved tools only when additional "
                            "risk context is materially required."
                        )
                    )
                ],
                "risk_analysis": None,
                "llm_calls": 0,
            },
            config={
                # Prevent runaway tool loops while you are learning.
                "recursion_limit": 10,
            },
        )

        return {
            "risk_analysis": result["risk_analysis"],
        }

    return risk_investigation_node