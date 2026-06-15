from app.models.claims_workflow_state import ClaimreviewState


def create_risk_investigation_node(risk_agent_graph):

    def risk_investigation_node(state: ClaimreviewState):
        result = risk_agent_graph.invoke(
            {
                "case_packet": state.case_packet,
                "messages": [],
                "risk_analysis": None,
                "tool_results": {},
                "previous_tool_calls": [],
                "selected_tool_decision": None,
                "latest_tool_result": None,
                "llm_calls": 0,
            },
            config={
                "recursion_limit": 10,
                "configurable": {
                    "thread_id": str(state.case_packet.workflow_run_id)
                }
            },
        )

        return {
            "risk_analysis": result["risk_analysis"],
            "tool_results": result.get("tool_results", {}),
            "previous_tool_calls": result.get("previous_tool_calls", []),
        }

    return risk_investigation_node
