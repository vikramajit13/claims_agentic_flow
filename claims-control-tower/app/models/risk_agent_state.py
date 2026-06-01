# app/schemas/risk_agent_state.py

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langchain.messages import AnyMessage

from app.schemas.case_packet_schema import CasePacketSchema
from app.schemas.risk_analysis_schema import RiskAnalysisSchema


class RiskAgentState(TypedDict):
    case_packet: CasePacketSchema

    # New AI and ToolMessages are appended rather than replacing history.
    messages: Annotated[list[AnyMessage], operator.add]

    risk_analysis: RiskAnalysisSchema | None

    llm_calls: int