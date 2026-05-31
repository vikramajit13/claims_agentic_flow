from pydantic import BaseModel, Field

from app.models.human_task import HumanTaskPriority


class InformationGap(BaseModel):
    gap: str = Field(..., description="Description of the missing context.")
    suggested_tool: str = Field(..., description="Name of the permitted read-only tool that could help.")
    priority: HumanTaskPriority = Field(..., description="Priority of resolving the information gap.")


class InformationGapAnalysis(BaseModel):
    investigation_required: bool = Field(..., description="Whether more tool-based investigation is recommended.")
    information_gaps: list[InformationGap] = Field(default_factory=list, description="Known information gaps.")


class ToolDecision(BaseModel):
    selected_tool: str | None = Field(default=None, description="Permitted tool selected for the next call.")
    tool_arguments: dict = Field(default_factory=dict, description="Arguments for the selected tool.")
    reason: str = Field(..., description="Reason for choosing this tool.")


class ToolExecutionRecord(BaseModel):
    tool_name: str = Field(..., description="Name of the executed tool.")
    tool_arguments: dict = Field(default_factory=dict, description="Arguments passed to the tool.")
    reason: str = Field(..., description="Why the tool was selected.")
    result: dict = Field(default_factory=dict, description="Structured tool output.")
