from enum import Enum
from typing import List
from pydantic import BaseModel, Field

from app.enums import FraudRiskLevel, RecommendationDecision

class RiskFactor(BaseModel):
    risk: str = Field(..., description="The identified risk factor name.")
    severity: FraudRiskLevel = Field(..., description="The severity level of the risk.")
    explanation: str = Field(..., description="Detailed explanation of the risk factor.")

class DecisionOption(BaseModel):
    decision: RecommendationDecision = Field(..., description="The proposed decision action.")
    when_to_use: str = Field(..., description="Criteria for selecting this decision.")

class ClaimReviewSchema(BaseModel):
    briefing_summary: str = Field(..., description="High-level summary of why the claim requires review.")
    why_workflow_paused: List[str] = Field(..., description="List of reasons triggering the workflow pause.")
    key_risk_factors: List[RiskFactor] = Field(..., description="Structured breakdown of specific risk metrics.")
    evidence_concerns: List[str] = Field(..., description="Gaps or anomalies found in the provided evidence.")
    recommended_adjuster_actions: List[str] = Field(..., description="Next steps for the claims adjuster to take.")
    questions_for_customer_or_repairer: List[str] = Field(..., description="Specific questions to resolve the discrepancies.")
    decision_options: List[DecisionOption] = Field(..., description="Available final decision paths and their logic.")
    customer_safe_message: str = Field(..., description="External-facing message suitable to share with the customer.")
