from pydantic import BaseModel
from app.schemas.claim_schema import ClaimSummarySchema
from app.schemas.policy_schema import PolicySummarySchema

class CasePacketSchema(BaseModel):
    claim_summary:  ClaimSummarySchema
    policy_summary: PolicySummarySchema 
    coverage_result: dict | None
    evidence_result: dict | None
    risk_result: dict | None
    guardrail_results: list[dict] | None
    adjudication_recommendation: dict | None
    claim_history_summary: dict | None