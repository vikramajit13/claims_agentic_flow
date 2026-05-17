from pydantic import BaseModel

class ClaimsWorkflowState(BaseModel):
    claim_id: str
    workflow_run_id: str
    policy_id: str
    claim_amount: float
    incident_date: str
    documents: list[dict]
    coverage_result: dict | None
    evidence_result: dict | None
    fraud_result: dict | None
    adjudication_result: dict | None
    human_review_result: dict | None
    payment_guardrail_result: dict | None
    final_status: str
    audit_events: list[dict]
    requires_human_review: bool