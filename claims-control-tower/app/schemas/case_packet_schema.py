from pydantic import BaseModel, Field
from app.schemas.claim_schema import ClaimSummarySchema
from app.schemas.policy_schema import PolicySummarySchema

class CasePacketSchema(BaseModel):
    workflow_run_id: int | None = None
    claim_summary:  ClaimSummarySchema
    policy_summary: PolicySummarySchema 
    documents: list[dict] = Field(default_factory=list)
    coverage_result: dict | None
    evidence_result: dict | None
    risk_result: dict | None
    guardrail_results: list[dict] | None
    adjudication_recommendation: dict | None
    claim_history_summary: dict | None


CasePacket = CasePacketSchema
