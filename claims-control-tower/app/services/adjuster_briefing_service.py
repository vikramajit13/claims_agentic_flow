# Adjuster Briefing Service
# accept case_packet as input and generate a briefing for the adjuster
# Invoke the LLM service to generate the briefing
# Return the briefing in a structured format defined by AdjusterBriefingSchema

from .AI.llm_client import llm_service

class AdjusterBriefingService:
    def __init__(self):
        self.llm_service = llm_service

    def generate_briefing(self, case_packet):
        # Here we would call the LLM service with the case packet to generate the briefing
        briefing = self.llm_service.generate_briefing(case_packet)
        return briefing