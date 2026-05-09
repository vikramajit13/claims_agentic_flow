from typing import Optional

from pydantic import BaseModel

from app.models.human_task import HumanTask
from app.schemas.workflow_schema import WorkflowExecutionResponse


class HumanTaskDecisionRequest(BaseModel):
    reviewer_id: str
    decision: str
    decision_notes: Optional[str] = None


class HumanTaskCompletionResponse(BaseModel):
    task: HumanTask
    workflow_result: WorkflowExecutionResponse
