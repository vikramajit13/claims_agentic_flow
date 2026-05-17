from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

class PolicySummarySchema(BaseModel):
    policy_id: UUID
    policy_number: str
    status: str
    active_from: date
    active_to: date
    coverage_limit: Decimal