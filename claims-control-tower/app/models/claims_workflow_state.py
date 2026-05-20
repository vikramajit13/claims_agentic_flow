from pydantic import BaseModel, Field
from app.schemas.case_packet_schema import CasePacketSchema
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema

    
class ClaimreviewState(BaseModel):
    case_packet: CasePacketSchema
    evidence_analysis: EvidenceAnalysisSchema | None = None
    #risk_analysis: RiskAnalysisSchema | None = None
    #adjuster_briefing: AdjusterBriefingSchema | None = None
    #recommended_next_action: str | None = None
    errors: list[str] = Field(default_factory=list)


ClaimsWorkflowState = ClaimreviewState
