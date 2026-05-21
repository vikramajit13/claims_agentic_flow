from app.enums import NextWorkflowAction, RecommendationDecision
from app.models.claims_workflow_state import ClaimreviewState
from app.models.human_task import HumanTaskPriority, HumanTaskType
from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.next_action_recommendation_schema import NextActionRecommendation
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService


def route_next_action_node(state: ClaimreviewState):
    case_packet = state.case_packet
    evidence_analysis = state.evidence_analysis
    risk_analysis = state.risk_analysis
    adjuster_briefing = state.adjuster_briefing
    if evidence_analysis is not None and isinstance(evidence_analysis, dict):
        evidence_analysis = EvidenceAnalysisSchema(**evidence_analysis)
    if risk_analysis is not None and isinstance(risk_analysis, dict):
        risk_analysis = RiskAnalysisSchema(**risk_analysis)
    if adjuster_briefing is not None and isinstance(adjuster_briefing, dict):
        adjuster_briefing = AdjusterBriefingSchema(**adjuster_briefing)
    if evidence_analysis is None or risk_analysis is None or adjuster_briefing is None:
        raise ValueError("route_next_action_node requires evidence_analysis, risk_analysis, and adjuster_briefing in state")

    prompt = PromptService().generate_next_action_prompt(
        case_packet,
        evidence_analysis,
        risk_analysis,
        adjuster_briefing,
    )
    fallback = _build_fallback_recommendation(case_packet, evidence_analysis, risk_analysis)
    recommendation = OllamaAsyncService().generate_structured(prompt, fallback.dict())
    return {"recommended_next_action": recommendation}


def _build_fallback_recommendation(case_packet, evidence_analysis, risk_analysis) -> NextActionRecommendation:
    adjudication = case_packet.adjudication_recommendation or {}
    guardrail_results = case_packet.guardrail_results or []
    decision = adjudication.get("recommendation") or adjudication.get("decision")
    supporting_factors = []
    blocking_reasons = []
    task_type = None
    priority = HumanTaskPriority.MEDIUM

    supporting_factors.extend(evidence_analysis.evidence_concerns)
    supporting_factors.extend(evidence_analysis.missing_information)
    supporting_factors.extend(risk_analysis.key_risk_drivers or risk_analysis.primary_risk_drivers)
    supporting_factors.extend(
        result.get("message", "")
        for result in guardrail_results
        if result.get("decision") == "REVIEW_REQUIRED" and result.get("message")
    )

    if decision == RecommendationDecision.REJECT.value:
        blocking_reasons.append(adjudication.get("reason", "Adjudication recommended rejection."))
        return NextActionRecommendation(
            next_action=NextWorkflowAction.BLOCK_RECOMMENDED,
            reason=blocking_reasons[0],
            task_type=None,
            priority=HumanTaskPriority.HIGH,
            requires_human_review=False,
            requires_more_information=False,
            blocking_reasons=blocking_reasons,
            supporting_factors=[factor for factor in supporting_factors if factor],
        )

    if evidence_analysis.missing_information or decision == RecommendationDecision.REQUEST_MORE_INFO.value:
        return NextActionRecommendation(
            next_action=NextWorkflowAction.REQUEST_MORE_INFO,
            reason="More information is recommended before proceeding due to missing or incomplete evidence.",
            task_type=HumanTaskType.EVIDENCE_REVIEW,
            priority=HumanTaskPriority.HIGH,
            requires_human_review=False,
            requires_more_information=True,
            blocking_reasons=[],
            supporting_factors=[factor for factor in supporting_factors if factor],
        )

    review_messages = [
        result.get("message", "")
        for result in guardrail_results
        if result.get("decision") == "REVIEW_REQUIRED" and result.get("message")
    ]
    if (
        decision == RecommendationDecision.REFER_TO_HUMAN.value
        or risk_analysis.risk_level.value == "HIGH"
        or evidence_analysis.evidence_quality.lower() == "questionable"
        or review_messages
    ):
        codes = {result.get("code") for result in guardrail_results}
        if {"INVOICE_DATE_BEFORE_INCIDENT", "REPEAT_CLAIMS_REVIEW_REQUIRED"}.issubset(codes):
            task_type = HumanTaskType.PAYMENT_REVIEW
        elif risk_analysis.risk_level.value == "HIGH":
            task_type = HumanTaskType.FRAUD_REVIEW
        else:
            task_type = HumanTaskType.CLAIM_REVIEW
        return NextActionRecommendation(
            next_action=NextWorkflowAction.CREATE_HUMAN_REVIEW_TASK,
            reason=adjudication.get("reason")
            or "The claim requires human review due to risk, evidence, or guardrail concerns.",
            task_type=task_type,
            priority=HumanTaskPriority.HIGH,
            requires_human_review=True,
            requires_more_information=False,
            blocking_reasons=[],
            supporting_factors=[factor for factor in supporting_factors if factor],
        )

    return NextActionRecommendation(
        next_action=NextWorkflowAction.PROCEED_TO_PAYMENT_GUARDRAILS,
        reason="The claim can proceed to payment guardrails based on the current evidence and risk posture.",
        task_type=None,
        priority=priority,
        requires_human_review=False,
        requires_more_information=False,
        blocking_reasons=[],
        supporting_factors=[factor for factor in supporting_factors if factor],
    )
