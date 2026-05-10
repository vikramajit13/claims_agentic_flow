from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GuardrailDecision(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class GuardrailSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GuardrailCategory(str, Enum):
    POLICY = "POLICY"
    CLAIM = "CLAIM"
    FRAUD_RISK = "FRAUD_RISK"
    PAYMENT = "PAYMENT"


class GuardrailResult(BaseModel):
    code: str
    category: GuardrailCategory
    decision: GuardrailDecision
    severity: GuardrailSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class GuardrailEvaluationSummary(BaseModel):
    overall_decision: GuardrailDecision
    results: list[GuardrailResult] = Field(default_factory=list)

    @property
    def blocking_results(self) -> list[GuardrailResult]:
        return [result for result in self.results if result.decision == GuardrailDecision.BLOCK]

    @property
    def review_results(self) -> list[GuardrailResult]:
        return [result for result in self.results if result.decision == GuardrailDecision.REVIEW_REQUIRED]

    @property
    def passed_results(self) -> list[GuardrailResult]:
        return [result for result in self.results if result.decision == GuardrailDecision.PASS]
