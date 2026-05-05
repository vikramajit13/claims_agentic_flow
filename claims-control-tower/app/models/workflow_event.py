
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum   

class WorkflowEventType(str, Enum):
    CLAIM_SUBMITTED = "claim_submitted"
    WORKFLOW_STARTED = "workflow_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    POLICY_VALIDATED = "policy_validated"
    DOCUMENTS_VALIDATED = "documents_validated"
    FRAUD_RULES_EVALUATED = "fraud_rules_evaluated"
    RECOMMENDATION_CREATED = "recommendation_created"
    HUMAN_TASK_CREATED = "human_task_created"
    HUMAN_TASK_COMPLETED = "human_task_completed"
    PAYMENT_GUARDRAIL_PASSED = "payment_guardrail_passed"
    PAYMENT_GUARDRAIL_FAILED = "payment_guardrail_failed"
    PAYMENT_INSTRUCTION_CREATED = "payment_instruction_created"
    WORKFLOW_COMPLETED = "workflow_completed"
    
class ACTOR_TYPE(str, Enum):
    SYSTEM = "system"
    RULE_ENGINE = "rule_engine"
    HUMAN_REVIEWER = "human_reviewer"
    PAYMENT_SERVICE = "payment_service"

class WorkflowEvent(BaseModel):
    id: int = Field(..., description="Unique identifier for the workflow event")
    workflow_run_id: int = Field(..., description="Unique identifier for the workflow run")
    claim_id: int = Field(..., description="Unique identifier for the claim")
    event_type: WorkflowEventType = Field(default=WorkflowEventType.STEP_STARTED, description="Type of the workflow event (e.g., 'step_started', 'step_completed')")
    step_name: str = Field(..., description="Name of the workflow step")
    actor_type: ACTOR_TYPE = Field(default=ACTOR_TYPE.SYSTEM, description="Type of actor triggering the event")
    actor_id: str = Field(..., description="Identifier for the actor (e.g., user ID, system component name)")
    event_payload: dict = Field(..., description="Additional data related to the event")
    created_at: str = Field(..., description="Timestamp when the event was created")