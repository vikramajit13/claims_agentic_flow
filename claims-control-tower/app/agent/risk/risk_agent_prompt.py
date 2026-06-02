import json

from app.schemas.investigation_schema import ToolDecision
from app.schemas.risk_analysis_schema import RiskAnalysisSchema


RISK_AGENT_SYSTEM_PROMPT = """
You are an internal insurance claims risk investigation assistant.

Your role:
- Analyse deterministic risk facts supplied in the case packet.
- Use approved read-only tools only when additional context is needed.
- Identify risk drivers that require adjuster attention.
- Produce evidence-based internal analysis.

Rules:
- Do not approve or reject a claim.
- Do not modify payout amounts.
- Do not create payment instructions.
- Do not override deterministic guardrails.
- Do not accuse the customer of fraud.
- Do not invent facts.
- Call tools only from the provided allowlist.
- Use tool outputs only as supporting context.
""".strip()


def _schema_json(model_class) -> dict:
    if hasattr(model_class, "model_json_schema"):
        return model_class.model_json_schema()
    return model_class.schema()


def generate_risk_tool_decision_prompt(case_packet, tool_results, previous_tool_calls, available_tools) -> str:
    packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
    prior_calls = [call.dict() if hasattr(call, "dict") else dict(call) for call in previous_tool_calls]
    schema_json = _schema_json(ToolDecision)
    return (
        f"{RISK_AGENT_SYSTEM_PROMPT}\n"
        "Decide whether one additional read-only tool call is required to improve risk analysis.\n"
        "If more context is required, call the best tool directly.\n"
        "If no more tool context is required, do not call a tool and answer with a concise summary.\n"
        "Prioritize repeat-claim risk, prior rejection context, policy ambiguity, document anomalies, and deterministic guardrails.\n"
        "Avoid repeating the same tool unless the context is still unresolved.\n"
        "When you answer without a tool call, return only JSON matching this schema.\n"
        f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
        f"Available tools: {json.dumps(available_tools, ensure_ascii=True)}\n"
        f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
        f"Current tool results: {json.dumps(tool_results, ensure_ascii=True)}\n"
        f"Previous tool calls: {json.dumps(prior_calls, ensure_ascii=True)}"
    )


def generate_final_risk_analysis_prompt(case_packet, tool_results) -> str:
    packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
    schema_json = _schema_json(RiskAnalysisSchema)
    return (
        f"{RISK_AGENT_SYSTEM_PROMPT}\n"
        "Return the final structured risk analysis.\n"
        "Use only the supplied case packet and retrieved tool outputs.\n"
        "Do not make a final claim or payment decision.\n"
        "Return only JSON matching this schema.\n"
        f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
        f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
        f"Tool results: {json.dumps(tool_results, ensure_ascii=True)}"
    )
