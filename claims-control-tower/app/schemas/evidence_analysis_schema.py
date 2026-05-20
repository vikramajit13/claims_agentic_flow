# create EvidenceAnalysisSchema based on below signature

from pydantic import BaseModel, Field


class EvidenceAnalysisSchema(BaseModel):
     evidence_quality: str = Field(..., description="Overall quality of the evidence (e.g., 'good', 'questionable', 'poor')")
     evidence_summary: str = Field(..., description="Summary of the evidence provided")
     evidence_concerns: list[str] = Field(default_factory=list, description="List of specific concerns or issues with the evidence")
     missing_information: list[str] = Field(default_factory=list, description="List of any missing information that is needed to fully assess the evidence")
     recommended_evidence_checks: list[str] = Field(default_factory=list, description="List of recommended checks or verifications to perform on the evidence")
