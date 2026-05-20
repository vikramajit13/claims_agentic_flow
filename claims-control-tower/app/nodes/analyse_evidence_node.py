# build node to analyse evidence
# extract documents, extract key information from documents, and prepare a summary for human review if needed
from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService


def analyse_evidence_node(state: ClaimreviewState):
    case_packet = state.case_packet
    prompt = PromptService().generate_evidence_analysis_prompt(case_packet)
    fallback = EvidenceAnalysisSchema(
        evidence_quality="good" if not case_packet.evidence_result or case_packet.evidence_result.get("is_valid", True) else "questionable",
        evidence_summary="Evidence analysis fallback generated from workflow context.",
        evidence_concerns=(case_packet.evidence_result or {}).get("reasons", []),
        missing_information=(case_packet.evidence_result or {}).get("missing_documents", []),
        recommended_evidence_checks=[
            "Review uploaded documents for completeness.",
            "Verify any flagged evidence concerns before final decisioning.",
        ],
    )

    evidence_analysis = OllamaAsyncService().generate_structured(prompt, fallback=fallback.dict())

    return {
        "evidence_analysis": evidence_analysis
    }
