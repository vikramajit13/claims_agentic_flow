from pydantic import BaseModel, Field
from app.schemas.case_packet_schema import CasePacketSchema
from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.investigation_schema import InformationGap, ToolDecision, ToolExecutionRecord
from app.schemas.next_action_recommendation_schema import NextActionRecommendation
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.tool.tools import SAFE_READ_ONLY_TOOLS

    
class ClaimreviewState(BaseModel):
    case_packet: CasePacketSchema
    evidence_analysis: EvidenceAnalysisSchema | None = None
    risk_analysis: RiskAnalysisSchema | None = None
    tool_results: dict[str, dict] = Field(default_factory=dict)
    information_gaps: list[InformationGap] = Field(default_factory=list)
    investigation_required: bool = False
    selected_tool_decision: ToolDecision | None = None
    previous_tool_calls: list[ToolExecutionRecord] = Field(default_factory=list)
    latest_tool_result: ToolExecutionRecord | None = None
    adjuster_briefing: AdjusterBriefingSchema | None = None
    recommended_next_action: NextActionRecommendation | None = None
    available_tools: list[str] = Field(default_factory=lambda: sorted(SAFE_READ_ONLY_TOOLS.keys()))
    errors: list[str] = Field(default_factory=list)


ClaimsWorkflowState = ClaimreviewState
