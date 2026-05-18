import json

from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema


class PromptService:
    def generate_adjuster_briefing_prompt(self, case_packet) -> str:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        schema_json = AdjusterBriefingSchema.schema()
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
