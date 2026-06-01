# app/agents/risk/risk_agent_graph.py

from typing import Literal

from langgraph.graph import END
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.models.risk_agent_state import RiskAgentState
from app.tool.risk_tools import create_risk_tools
from app.agent.risk.risk_agent_node import (
    create_finalise_risk_analysis_node,
    create_risk_agent_node,
)
from app.schemas.risk_analysis_schema import RiskAnalysisSchema


def route_after_risk_agent(state) -> Literal["risk_tools", "finalise"]:
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "risk_tools"

    return "finalise"


def create_risk_agent_graph(
    *,
    llm,
    claims_adapter,
):
    risk_tools = create_risk_tools(
        claims_adapter=claims_adapter,
    )

    model_with_tools = llm.bind_tools(risk_tools)

    structured_model = llm.with_structured_output(
        RiskAnalysisSchema
    )

    builder = StateGraph(RiskAgentState)

    builder.add_node(
        "risk_agent",
        create_risk_agent_node(model_with_tools),
    )

    builder.add_node(
        "risk_tools",
        ToolNode(risk_tools),
    )

    builder.add_node(
        "finalise",
        create_finalise_risk_analysis_node(structured_model),
    )

    builder.add_edge(START, "risk_agent")

    builder.add_conditional_edges(
        "risk_agent",
        route_after_risk_agent,
        {
            "risk_tools": "risk_tools",
            "finalise": "finalise",
        },
    )

    builder.add_edge("risk_tools", "risk_agent")
    builder.add_edge("finalise", END)

    return builder.compile()

risk_agent_graph = create_risk_agent_graph(
    llm=None,  # Injected at runtime to allow flexible configuration
    claims_adapter=None,  # Injected at runtime to allow flexible configuration
)