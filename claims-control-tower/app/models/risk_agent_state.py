from pydantic import BaseModel, Field

from app.schemas.case_packet_schema import CasePacketSchema
from app.schemas.investigation_schema import ToolDecision, ToolExecutionRecord
from app.schemas.risk_analysis_schema import RiskAnalysisSchema


class RiskAgentState(BaseModel):
    case_packet: CasePacketSchema
    messages: list = Field(default_factory=list)
    tool_results: dict[str, dict] = Field(default_factory=dict)
    selected_tool_decision: ToolDecision | None = None
    previous_tool_calls: list[ToolExecutionRecord] = Field(default_factory=list)
    latest_tool_result: ToolExecutionRecord | None = None
    risk_analysis: RiskAnalysisSchema | None = None
    llm_calls: int = 0
