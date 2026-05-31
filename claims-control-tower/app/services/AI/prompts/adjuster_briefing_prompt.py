import json

from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.investigation_schema import InformationGapAnalysis, ToolDecision
from app.schemas.next_action_recommendation_schema import NextActionRecommendation
from app.schemas.risk_analysis_schema import RiskAnalysisSchema


class PromptService:
    @staticmethod
    def _schema_json(model_class) -> dict:
        if hasattr(model_class, "model_json_schema"):
            return model_class.model_json_schema()
        return model_class.schema()

    def generate_adjuster_briefing_prompt(self, case_packet) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        schema_json = self._schema_json(AdjusterBriefingSchema)
        return (
            "You are an internal insurance claim review assistant.\n"
            "You do not make final claim decisions.\n"
            "You do not approve, reject, or create payment instructions.\n"
            "You prepare a structured internal briefing for a human adjuster.\n"
            "Use only the supplied case packet.\n"
            "Do not invent facts.\n"
            "If information is missing, say what needs to be verified.\n"
            "Do not accuse the customer of fraud.\n"
            "Do not reveal internal fraud scoring in the customer-facing message.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}"
        )

    def generate_adjuster_briefing_graph_prompt(self, case_packet, evidence_analysis, risk_analysis, tool_results=None) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        evidence = evidence_analysis.dict() if hasattr(evidence_analysis, "dict") else dict(evidence_analysis)
        risk = risk_analysis.dict() if hasattr(risk_analysis, "dict") else dict(risk_analysis)
        tool_payload = tool_results or {}
        schema_json = self._schema_json(AdjusterBriefingSchema)
        return (
            "You are an internal insurance claims adjuster assistant.\n"
            "Prepare a structured briefing for a human reviewer.\n"
            "Use only the supplied claim case packet, evidence analysis, risk analysis, and read-only tool results.\n"
            "Do not invent facts.\n"
            "Do not make the final claim decision.\n"
            "Do not accuse the customer of fraud.\n"
            "Keep the customer-safe message neutral and professional.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
            f"Evidence analysis: {json.dumps(evidence, ensure_ascii=True)}\n"
            f"Risk analysis: {json.dumps(risk, ensure_ascii=True)}\n"
            f"Tool results: {json.dumps(tool_payload, ensure_ascii=True)}"
        )

    def generate_evidence_analysis_prompt(self, case_packet) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        schema_json = self._schema_json(EvidenceAnalysisSchema)
        return (
            "You are an internal insurance evidence review assistant.\n"
            "Use only the supplied case packet.\n"
            "Assess evidence quality, evidence concerns, missing information, and recommended evidence checks.\n"
            "Do not invent facts.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}"
        )

    def generate_risk_analysis_prompt(self, case_packet, evidence_analysis) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        evidence = evidence_analysis.dict() if hasattr(evidence_analysis, "dict") else dict(evidence_analysis)
        schema_json = self._schema_json(RiskAnalysisSchema)
        return (
            "You are an internal insurance risk triage assistant.\n"
            "Use only the supplied case packet and evidence analysis.\n"
            "Summarize the risk posture, identify the key risk drivers, and say whether human review is warranted.\n"
            "Do not invent facts.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
            f"Evidence analysis: {json.dumps(evidence, ensure_ascii=True)}"
        )

    def generate_next_action_prompt(self, case_packet, evidence_analysis, risk_analysis, adjuster_briefing, tool_results=None) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        evidence = evidence_analysis.dict() if hasattr(evidence_analysis, "dict") else dict(evidence_analysis)
        risk = risk_analysis.dict() if hasattr(risk_analysis, "dict") else dict(risk_analysis)
        briefing = adjuster_briefing.dict() if hasattr(adjuster_briefing, "dict") else dict(adjuster_briefing)
        tool_payload = tool_results or {}
        schema_json = self._schema_json(NextActionRecommendation)
        return (
            "You are an internal insurance workflow routing assistant.\n"
            "Recommend the next workflow action only; do not execute it.\n"
            "Use only the supplied case packet, evidence analysis, risk analysis, adjuster briefing, and read-only tool results.\n"
            "Choose one next_action from the allowed enum values.\n"
            "Consider adjudication recommendation, guardrail results, evidence quality, missing information, risk level, and key risk drivers.\n"
            "Do not invent facts.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
            f"Evidence analysis: {json.dumps(evidence, ensure_ascii=True)}\n"
            f"Risk analysis: {json.dumps(risk, ensure_ascii=True)}\n"
            f"Adjuster briefing: {json.dumps(briefing, ensure_ascii=True)}\n"
            f"Tool results: {json.dumps(tool_payload, ensure_ascii=True)}"
        )

    def generate_information_gap_prompt(self, case_packet, evidence_analysis, risk_analysis, tool_results, available_tools) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        evidence = evidence_analysis.dict() if hasattr(evidence_analysis, "dict") else dict(evidence_analysis)
        risk = risk_analysis.dict() if hasattr(risk_analysis, "dict") else dict(risk_analysis)
        schema_json = self._schema_json(InformationGapAnalysis)
        return (
            "You are an internal insurance investigation planner.\n"
            "You may only recommend additional read-only tools from the supplied available_tools list.\n"
            "Inspect the current case context and determine whether important information is still missing.\n"
            "Focus on claim history, prior rejection context, policy coverage interpretation, document metadata, and deterministic guardrail outcomes.\n"
            "Do not invent tools.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Available tools: {json.dumps(available_tools, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
            f"Evidence analysis: {json.dumps(evidence, ensure_ascii=True)}\n"
            f"Risk analysis: {json.dumps(risk, ensure_ascii=True)}\n"
            f"Tool results: {json.dumps(tool_results, ensure_ascii=True)}"
        )

    def generate_tool_decision_prompt(self, information_gaps, previous_tool_calls, available_tools, case_packet) -> str:
        gaps = [gap.dict() if hasattr(gap, "dict") else dict(gap) for gap in information_gaps]
        prior_calls = [call.dict() if hasattr(call, "dict") else dict(call) for call in previous_tool_calls]
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        schema_json = self._schema_json(ToolDecision)
        return (
            "You are an internal insurance investigation orchestrator.\n"
            "Select exactly one next read-only tool call, or select no tool if no further call is needed.\n"
            "Only choose from the available_tools list.\n"
            "Avoid repeating tool calls that are already present in previous_tool_calls unless the gap truly remains unresolved.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Available tools: {json.dumps(available_tools, ensure_ascii=True)}\n"
            f"Information gaps: {json.dumps(gaps, ensure_ascii=True)}\n"
            f"Previous tool calls: {json.dumps(prior_calls, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}"
        )
