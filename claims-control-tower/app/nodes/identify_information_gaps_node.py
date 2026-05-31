from app.models.claims_workflow_state import ClaimreviewState
from app.models.human_task import HumanTaskPriority
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.investigation_schema import InformationGap, InformationGapAnalysis
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService
from app.services.observability import traceable


@traceable(name="identify_information_gaps_node", run_type="chain")
def identify_information_gaps_node(state: ClaimreviewState):
    evidence_analysis = state.evidence_analysis
    risk_analysis = state.risk_analysis
    if evidence_analysis is not None and isinstance(evidence_analysis, dict):
        evidence_analysis = EvidenceAnalysisSchema(**evidence_analysis)
    if risk_analysis is not None and isinstance(risk_analysis, dict):
        risk_analysis = RiskAnalysisSchema(**risk_analysis)
    if evidence_analysis is None or risk_analysis is None:
        raise ValueError("identify_information_gaps_node requires evidence_analysis and risk_analysis in state")

    prompt = PromptService().generate_information_gap_prompt(
        state.case_packet,
        evidence_analysis,
        risk_analysis,
        state.tool_results,
        state.available_tools,
    )
    fallback = _build_fallback_gap_analysis(state, evidence_analysis, risk_analysis)
    gap_analysis = OllamaAsyncService().generate_structured(prompt, fallback.dict())
    return {
        "investigation_required": gap_analysis.get("investigation_required", False),
        "information_gaps": gap_analysis.get("information_gaps", []),
    }


def _build_fallback_gap_analysis(
    state: ClaimreviewState,
    evidence_analysis: EvidenceAnalysisSchema,
    risk_analysis: RiskAnalysisSchema,
) -> InformationGapAnalysis:
    case_packet = state.case_packet
    tool_results = state.tool_results
    guardrail_results = case_packet.guardrail_results or []
    gaps: list[InformationGap] = []
    guardrail_codes = {result.get("code") for result in guardrail_results}
    risk_drivers = " ".join(risk_analysis.key_risk_drivers or risk_analysis.primary_risk_drivers).lower()

    if (
        ("repeat" in risk_drivers or "claim history" in risk_drivers or "REPEAT_CLAIMS_REVIEW_REQUIRED" in guardrail_codes)
        and "get_claim_history" not in tool_results
    ):
        gaps.append(
            InformationGap(
                gap="Claim history required to validate repeat-claim risk.",
                suggested_tool="get_claim_history",
                priority=HumanTaskPriority.HIGH,
            )
        )

    if case_packet.claim_summary.previous_claim_id and "get_prior_rejection_details" not in tool_results:
        gaps.append(
            InformationGap(
                gap="Prior rejection details required for linked claim review.",
                suggested_tool="get_prior_rejection_details",
                priority=HumanTaskPriority.MEDIUM,
            )
        )

    has_invoice_doc = any(document.get("document_type") == "invoice" for document in case_packet.documents)
    if (
        (has_invoice_doc or "invoice" in " ".join(evidence_analysis.evidence_concerns).lower() or "INVOICE_DATE_BEFORE_INCIDENT" in guardrail_codes)
        and "get_document_metadata" not in tool_results
    ):
        gaps.append(
            InformationGap(
                gap="Structured invoice and repair document metadata is required to confirm evidence anomalies.",
                suggested_tool="get_document_metadata",
                priority=HumanTaskPriority.HIGH,
            )
        )

    coverage_reasons = (case_packet.coverage_result or {}).get("reasons", [])
    if (
        (coverage_reasons or case_packet.claim_summary.claim_amount >= case_packet.policy_summary.coverage_limit * 0.8)
        and "get_policy_coverage_summary" not in tool_results
    ):
        gaps.append(
            InformationGap(
                gap="Policy coverage summary is required to confirm limits, dates, and covered event types.",
                suggested_tool="get_policy_coverage_summary",
                priority=HumanTaskPriority.MEDIUM,
            )
        )

    if guardrail_results and "get_guardrail_results" not in tool_results and case_packet.workflow_run_id is not None:
        gaps.append(
            InformationGap(
                gap="Deterministic guardrail results are required to align AI reasoning with business controls.",
                suggested_tool="get_guardrail_results",
                priority=HumanTaskPriority.MEDIUM,
            )
        )

    return InformationGapAnalysis(
        investigation_required=bool(gaps),
        information_gaps=gaps,
    )
