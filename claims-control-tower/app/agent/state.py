from langgraph.graph import StateGraph
from app.models.claims_workflow_state import ClaimsWorkflowState

def create_claims_processing_state_graph()->StateGraph:
    claimsGraph = StateGraph(ClaimsWorkflowState)
    claimsGraph.add_node("ingest_claim", ingest_claims)
    return claimsGraph


        
