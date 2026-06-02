from app.agent.risk.risk_agent_node import (
    create_finalise_risk_analysis_node,
    create_risk_agent_node,
    merge_risk_tool_result_node,
)
from app.models.risk_agent_state import RiskAgentState
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.services.AI.chat_model_factory import create_langchain_chat_model
from app.tool.tools import (
    get_claim_history,
    get_document_metadata,
    get_guardrail_results,
    get_policy_coverage_summary,
    get_prior_rejection_details,
)
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode


RISK_AGENT_TOOLS = [
    get_claim_history,
    get_prior_rejection_details,
    get_policy_coverage_summary,
    get_document_metadata,
    get_guardrail_results,
]


def _route_after_risk_agent(state: RiskAgentState) -> str:
    if state.llm_calls >= 3:
        return "finalise"
    last_message = state.messages[-1] if state.messages else None
    tool_calls = getattr(last_message, "tool_calls", None) or []
    return "risk_tools" if tool_calls else "finalise"


def create_risk_agent_graph() -> CompiledStateGraph:
    model = create_langchain_chat_model()
    model_with_tools = model.bind_tools(RISK_AGENT_TOOLS)
    structured_model = model.with_structured_output(RiskAnalysisSchema)

    builder = StateGraph(RiskAgentState)
    builder.add_node("risk_agent", create_risk_agent_node(model_with_tools))
    builder.add_node("risk_tools", ToolNode(RISK_AGENT_TOOLS))
    builder.add_node("merge_tool_result", merge_risk_tool_result_node)
    builder.add_node("finalise", create_finalise_risk_analysis_node(structured_model))
    builder.set_entry_point("risk_agent")
    builder.add_conditional_edges(
        "risk_agent",
        _route_after_risk_agent,
        {
            "risk_tools": "risk_tools",
            "finalise": "finalise",
        },
    )
    builder.add_edge("risk_tools", "merge_tool_result")
    builder.add_edge("merge_tool_result", "risk_agent")
    builder.set_finish_point("finalise")
    return builder.compile()


risk_agent_graph = create_risk_agent_graph()
