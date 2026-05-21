from pydantic import BaseModel, Field

from app.enums import FraudRiskLevel


class RiskAnalysisSchema(BaseModel):
    risk_score: int = Field(..., ge=0, le=100, description="Normalized claim risk score from 0 to 100.")
    risk_level: FraudRiskLevel = Field(..., description="Overall risk level for the claim.")
    risk_summary: str = Field(..., description="Short internal summary of the key risk picture.")
    primary_risk_drivers: list[str] = Field(
        default_factory=list,
        description="Most material facts driving the current risk assessment.",
    )
    risk_mitigations: list[str] = Field(
        default_factory=list,
        description="Checks or controls that would reduce uncertainty before decisioning.",
    )
    requires_human_review: bool = Field(
        ...,
        description="Whether the current risk posture suggests manual review is prudent.",
    )
