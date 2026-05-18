from pydantic import BaseModel

class PolicySummarySchema(BaseModel):
    policy_id: int
    policy_number: str
    status: str
    active_from: str
    active_to: str
    coverage_limit: float
