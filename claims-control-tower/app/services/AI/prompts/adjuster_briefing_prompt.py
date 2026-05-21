import json

from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
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

    def generate_adjuster_briefing_graph_prompt(self, case_packet, evidence_analysis, risk_analysis) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        evidence = evidence_analysis.dict() if hasattr(evidence_analysis, "dict") else dict(evidence_analysis)
        risk = risk_analysis.dict() if hasattr(risk_analysis, "dict") else dict(risk_analysis)
        schema_json = self._schema_json(AdjusterBriefingSchema)
        return (
            "You are an internal insurance claims adjuster assistant.\n"
            "Prepare a structured briefing for a human reviewer.\n"
            "Use only the supplied claim case packet, evidence analysis, and risk analysis.\n"
            "Do not invent facts.\n"
            "Do not make the final claim decision.\n"
            "Do not accuse the customer of fraud.\n"
            "Keep the customer-safe message neutral and professional.\n"
            "Return only JSON matching this schema.\n"
            f"Schema: {json.dumps(schema_json, ensure_ascii=True)}\n"
            f"Case packet: {json.dumps(packet, ensure_ascii=True)}\n"
            f"Evidence analysis: {json.dumps(evidence, ensure_ascii=True)}\n"
            f"Risk analysis: {json.dumps(risk, ensure_ascii=True)}"
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
