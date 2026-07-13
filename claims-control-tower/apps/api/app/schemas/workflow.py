from pydantic import BaseModel, Field


class ClaimWorkflowState(BaseModel):
    workflow_id: int
    status: str
    assigned_to: str | None = None
    created_at: str
    updated_at: str
    workflow_steps: list[str] = Field(default_factory=list)
    current_step: str | None = None
    previous_step: str | None = None
    is_completed: bool = False
    is_error: bool = False
    error_message: str | None = None