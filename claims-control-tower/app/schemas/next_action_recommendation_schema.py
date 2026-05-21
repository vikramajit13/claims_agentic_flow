from pydantic import BaseModel, Field

from app.enums import NextWorkflowAction
from app.models.human_task import HumanTaskPriority, HumanTaskType


class NextActionRecommendation(BaseModel):
    next_action: NextWorkflowAction = Field(..., description="Recommended next workflow action.")
    reason: str = Field(..., description="Explanation for the recommended next action.")
    task_type: HumanTaskType | None = Field(
        default=None,
        description="Suggested human task type when human review is recommended.",
    )
    priority: HumanTaskPriority | None = Field(
        default=None,
        description="Suggested operational priority for the next action.",
    )
    requires_human_review: bool = Field(..., description="Whether a human reviewer is recommended.")
    requires_more_information: bool = Field(..., description="Whether more evidence or documents are recommended.")
    blocking_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons that suggest blocking or stopping automated progression.",
    )
    supporting_factors: list[str] = Field(
        default_factory=list,
        description="Observed factors that support the recommendation.",
    )
