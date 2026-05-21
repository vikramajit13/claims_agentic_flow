from enum import Enum

from pydantic import BaseModel, Field


class WorkflowEventType(str, Enum):
    CLAIM_SUBMITTED = "claim_submitted"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_WAITING_FOR_HUMAN = "workflow_waiting_for_human"
    WORKFLOW_WAITING_FOR_INFO = "workflow_waiting_for_info"
    BUSINESS_GUARDRAILS_EVALUATED = "business_guardrails_evaluated"
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
    AI_EVIDENCE_ANALYSIS_COMPLETED = "ai_evidence_analysis_completed"
    AI_RISK_ANALYSIS_COMPLETED = "ai_risk_analysis_completed"
    AI_ADJUSTER_BRIEFING_GENERATED = "ai_adjuster_briefing_generated"
    ADJUSTER_BRIEFING_CREATED = "adjuster_briefing_created"
    WORKFLOW_COMPLETED = "workflow_completed"


class ActorType(str, Enum):
    SYSTEM = "system"
    RULE_ENGINE = "rule_engine"
    HUMAN_REVIEWER = "human_reviewer"
    PAYMENT_SERVICE = "payment_service"


class WorkflowEvent(BaseModel):
    id: int = Field(..., description="Unique identifier for the workflow event")
    workflow_run_id: int = Field(..., description="Unique identifier for the workflow run")
    claim_id: int = Field(..., description="Unique identifier for the claim")
    event_type: WorkflowEventType = Field(..., description="Type of the workflow event")
    step_name: str = Field(..., description="Name of the workflow step")
    actor_type: ActorType = Field(default=ActorType.SYSTEM, description="Type of actor triggering the event")
    adjuster_briefing: dict | None = Field(default=None, description="Briefing for the adjuster, if applicable")
    actor_id: str = Field(..., description="Identifier for the actor")
    event_payload: dict = Field(..., description="Additional data related to the event")
    created_at: str = Field(..., description="Timestamp when the event was created")
