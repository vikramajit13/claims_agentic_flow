# app/agents/risk/risk_agent_nodes.py

from langchain.messages import HumanMessage, SystemMessage

from app.agent.risk.risk_agent_prompt import RISK_AGENT_SYSTEM_PROMPT



def format_risk_context(case_packet) -> str:
    return f"""
Assess risk for the following insurance claim.

Claim:
{case_packet.claim_summary.model_dump_json(indent=2)}

Deterministic risk result:
{case_packet.risk_result.model_dump_json(indent=2)}

Deterministic guardrail results:
{case_packet.guardrail_results}

Existing claim-history summary:
{case_packet.claim_history_summary}

Use tools only when additional context is materially required.
"""


def create_risk_agent_node(model_with_tools):

    def risk_agent_node(state):
        response = model_with_tools.invoke(
            [
                SystemMessage(content=RISK_AGENT_SYSTEM_PROMPT),
                HumanMessage(content=format_risk_context(state["case_packet"])),
                *state["messages"],
            ]
        )

        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    return risk_agent_node


def create_finalise_risk_analysis_node(structured_model):

    def finalise_risk_analysis_node(state):
        analysis = structured_model.invoke(
            [
                SystemMessage(
                    content=(
                        RISK_AGENT_SYSTEM_PROMPT
                        + """
Return the final structured risk analysis.
Use only the supplied case packet and retrieved tool outputs.
Do not make a final claim or payment decision.
"""
                    )
                ),
                HumanMessage(
                    content=format_risk_context(state["case_packet"])
                ),
                *state["messages"],
            ]
        )

        return {
            "risk_analysis": analysis,
        }

    return finalise_risk_analysis_node