import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.risk.risk_agent_prompt import (
    RISK_AGENT_SYSTEM_PROMPT,
    generate_risk_tool_decision_prompt,
    generate_final_risk_analysis_prompt,
)
from app.schemas.investigation_schema import ToolExecutionRecord
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.services.observability import traceable


@traceable(name="risk_agent_reason_node", run_type="chain")
def create_risk_agent_node(model_with_tools):
    def risk_agent_node(state):
        prompt = generate_risk_tool_decision_prompt(
            state.case_packet,
            state.tool_results,
            state.previous_tool_calls,
            [
                "get_claim_history",
                "get_prior_rejection_details",
                "get_policy_coverage_summary",
                "get_document_metadata",
                "get_guardrail_results",
            ],
        )
        response = model_with_tools.invoke(
            [
                SystemMessage(content=RISK_AGENT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
                *state.messages,
            ]
        )
        return {
            "messages": [*state.messages, response],
            "llm_calls": state.llm_calls + 1,
        }

    return risk_agent_node


@traceable(name="risk_agent_merge_tool_result_node", run_type="chain")
def merge_risk_tool_result_node(state):
    tool_results = dict(state.tool_results)
    previous_tool_calls = list(state.previous_tool_calls)

    for message in state.messages:
        tool_call_id = getattr(message, "tool_call_id", None)
        tool_name = getattr(message, "name", None)
        if tool_call_id is None or not tool_name or tool_name in tool_results:
            continue
        parsed_result = _parse_tool_result_content(getattr(message, "content", ""))
        tool_results[tool_name] = parsed_result
        previous_tool_calls.append(
            ToolExecutionRecord(
                tool_name=tool_name,
                tool_arguments={},
                reason="Tool executed by risk agent through ToolNode.",
                result=parsed_result,
            )
        )

    return {
        "tool_results": tool_results,
        "previous_tool_calls": previous_tool_calls,
    }


@traceable(name="risk_agent_finalise_node", run_type="chain")
def create_finalise_risk_analysis_node(structured_model):
    def finalise_risk_analysis_node(state):
        prompt = generate_final_risk_analysis_prompt(
            state.case_packet,
            state.tool_results,
        )
        analysis = structured_model.invoke(
            [
                SystemMessage(content=RISK_AGENT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
                *state.messages,
            ]
        )
        if isinstance(analysis, RiskAnalysisSchema):
            return {"risk_analysis": analysis}
        return {"risk_analysis": RiskAnalysisSchema(**analysis)}

    return finalise_risk_analysis_node


def _parse_tool_result_content(content):
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        return {"content": content}
    if isinstance(content, str):
        try:
            return json.loads(content)
        except Exception:
            return {"content": content}
    return {"content": content}
