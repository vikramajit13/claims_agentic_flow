from __future__ import annotations

from app.enums import FraudRiskLevel, RecommendationDecision
from app.schemas.Adjuster_briefing_schema import (
    AdjusterBriefingSchema,
    DecisionOption,
    RiskFactor,
)
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService


class AdjusterBriefingAgent:
    def __init__(self, llm_service: OllamaAsyncService | None = None, prompt_service: PromptService | None = None):
        self.llm_service = llm_service or OllamaAsyncService()
        self.prompt_service = prompt_service or PromptService()

    def generate_briefing(self, case_packet) -> AdjusterBriefingSchema:
        prompt = self.prompt_service.generate_adjuster_briefing_prompt(case_packet)
        fallback = self._build_fallback_briefing(case_packet)
        briefing_payload = self.llm_service.generate_structured(prompt, fallback.dict())
        return AdjusterBriefingSchema(**briefing_payload)

    def _build_fallback_briefing(self, case_packet) -> AdjusterBriefingSchema:
        packet = case_packet.dict() if hasattr(case_packet, "dict") else dict(case_packet)
        recommendation = packet.get("adjudication_recommendation") or {}
        risk_result = packet.get("risk_result") or {}
        evidence_result = packet.get("evidence_result") or {}
        guardrail_results = packet.get("guardrail_results") or []
        claim_summary = packet.get("claim_summary") or {}

        paused_reasons = []
        if recommendation.get("reason"):
            paused_reasons.append(recommendation["reason"])
        paused_reasons.extend(result.get("message", "") for result in guardrail_results if result.get("message"))
        paused_reasons = [reason for reason in paused_reasons if reason]

        risk_factors = []
        for factor in risk_result.get("risk_factors", []):
            risk_factors.append(
                RiskFactor(
                    risk=factor,
                    severity=FraudRiskLevel.HIGH if risk_result.get("risk_level") == "HIGH" else FraudRiskLevel.MEDIUM,
                    explanation=factor,
                )
            )
        for result in guardrail_results:
            if result.get("decision") == "REVIEW_REQUIRED":
                risk_factors.append(
                    RiskFactor(
                        risk=result.get("code", "GUARDRAIL_REVIEW"),
                        severity=FraudRiskLevel.HIGH,
                        explanation=result.get("message", "Business guardrail triggered review"),
                    )
                )

        evidence_concerns = list(evidence_result.get("missing_documents", []))
        evidence_concerns.extend(evidence_result.get("reasons", []))

        questions = []
        for concern in evidence_concerns:
            questions.append(f"Can you clarify or provide evidence for: {concern}?")
        if not questions and paused_reasons:
            questions = [f"Can you explain: {paused_reasons[0]}?"]

        return AdjusterBriefingSchema(
            briefing_summary=f"Claim {claim_summary.get('claim_id')} requires adjuster review before a final decision.",
            why_workflow_paused=paused_reasons or ["Manual review required based on adjudication recommendation."],
            key_risk_factors=risk_factors,
            evidence_concerns=evidence_concerns,
            recommended_adjuster_actions=[
                "Review the claim timeline and supporting evidence.",
                "Confirm whether the recommendation should be approved, rejected, or modified.",
                "Document the rationale clearly for audit purposes.",
            ],
            questions_for_customer_or_repairer=questions,
            decision_options=[
                DecisionOption(
                    decision=RecommendationDecision.APPROVE,
                    when_to_use="Use when the evidence supports the claim and no unresolved risks remain.",
                ),
                DecisionOption(
                    decision=RecommendationDecision.REJECT,
                    when_to_use="Use when material inconsistencies or policy violations remain unresolved.",
                ),
                DecisionOption(
                    decision=RecommendationDecision.REQUEST_MORE_INFO,
                    when_to_use="Use when more evidence is needed before reaching a decision.",
                ),
            ],
            customer_safe_message="Your claim is under specialist review. We may contact you shortly if we need any clarification.",
        )


AdjusterBriefingService = AdjusterBriefingAgent
