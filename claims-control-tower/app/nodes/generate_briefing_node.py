from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.risk_analysis_schema import RiskAnalysisSchema
from app.services.AI.llm_client import OllamaAsyncService
from app.services.AI.prompts.adjuster_briefing_prompt import PromptService
from app.services.adjuster_briefing_service import AdjusterBriefingAgent
from app.services.observability import traceable

@traceable(name="generate_briefing_node", run_type="chain")
def generate_briefing_node(state: ClaimreviewState):
    case_packet = state.case_packet
    evidence_analysis = state.evidence_analysis
    risk_analysis = state.risk_analysis
    if evidence_analysis is not None and isinstance(evidence_analysis, dict):
        evidence_analysis = EvidenceAnalysisSchema(**evidence_analysis)
    if risk_analysis is not None and isinstance(risk_analysis, dict):
        risk_analysis = RiskAnalysisSchema(**risk_analysis)
    if evidence_analysis is None or risk_analysis is None:
        raise ValueError("generate_briefing_node requires evidence_analysis and risk_analysis in state")

    prompt = PromptService().generate_adjuster_briefing_graph_prompt(
        case_packet,
        evidence_analysis,
        risk_analysis,
    )
    fallback = AdjusterBriefingAgent()._build_fallback_briefing(case_packet)
    briefing = OllamaAsyncService().generate_structured(prompt, fallback.dict())
    return {"adjuster_briefing": briefing}
