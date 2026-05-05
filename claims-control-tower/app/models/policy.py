
from pydantic import BaseModel, Field
from enum import Enum


class PolicyType(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class Policy(BaseModel):
    id: int = Field(..., description="Unique identifier for the policy")
    policy_number: str = Field(..., description="Unique policy number")
    customer_id: int = Field(..., description="ID of the customer associated with the policy")
    policy_type: PolicyType = Field(default=PolicyType.ACTIVE, description="Type of the policy (e.g., 'auto', 'home', 'health')")
    coverage_limit: float = Field(..., description="Coverage limit of the policy")
    deductible: float = Field(..., description="Deductible amount for the policy")
    active_from: str = Field(..., description="Start date of the policy coverage (YYYY-MM-DD)")
    active_to: str = Field(..., description="End date of the policy coverage (YYYY-MM-DD)")
    status: str = Field(..., description="Current status of the policy (e.g., 'active', 'inactive')")
    covered_claim_types: list[str] = Field(..., description="List of claim types covered by the policy")


