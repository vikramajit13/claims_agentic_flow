from app.enums import FraudRiskLevel
from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService


def analyse_risk_node(state: ClaimreviewState):
    case_packet = state.case_packet
    evidence_analysis = state.evidence_analysis
    if evidence_analysis is not None and isinstance(evidence_analysis, dict):
        evidence_analysis = EvidenceAnalysisSchema(**evidence_analysis)
    prompt = PromptService().generate_risk_analysis_prompt(case_packet, evidence_analysis)
    risk_result = case_packet.risk_result or {}
    risk_score = int(risk_result.get("risk_score", 0))
    risk_level = risk_result.get("risk_level", FraudRiskLevel.LOW.value)
    risk_factors = list(risk_result.get("risk_factors", []))
    if evidence_analysis:
        risk_factors.extend(evidence_analysis.evidence_concerns)
        risk_factors.extend(evidence_analysis.missing_information)
    fallback = RiskAnalysisSchema(
        risk_score=max(0, min(100, risk_score)),
        risk_level=FraudRiskLevel(risk_level),
        risk_summary="Risk analysis fallback generated from workflow context.",
        primary_risk_drivers=risk_factors,
        key_risk_drivers=risk_factors,
        risk_mitigations=[
            "Validate any missing or contradictory evidence before finalizing the claim.",
            "Confirm the claim timeline against policy and document dates.",
        ],
        requires_human_review=risk_level == FraudRiskLevel.HIGH.value or risk_score >= 70,
    )
    risk_analysis = OllamaAsyncService().generate_structured(prompt, fallback=fallback.dict())
    return {"risk_analysis": risk_analysis}
