import asyncio

from app.graph import GraphStateManagerFactory
from app.graph.state import ClaimGraphState
from app.nodes.start_claim import process_claim


def test_graph_manager_compiles():
    manager = GraphStateManagerFactory().create()
    graph = manager.compile()
    assert graph is not None


def test_graph_manager_supports_new_graph_keys():
    assert GraphStateManagerFactory.get_definition("customer_history").name == "customer_history_graph"
    assert GraphStateManagerFactory.get_definition("document_evidence").name == "document_evidence_graph"


def test_start_claim_node_loads_claim_context(client):
    claim = client.post(
        "/v1/claims",
        json={
            "claim_number": "GRAPH-001",
            "customer_id": 99,
            "claim_type": "motor",
            "description": "Broken windscreen",
            "claim_amount": 2400,
        },
    ).json()

    result = asyncio.run(process_claim(ClaimGraphState(claim_id=claim["id"])))

    assert result["claim_id"] == claim["id"]
    assert result["claim_status"] == "ready_for_graph"
    assert result["current_step"] == "graph_bootstrap"
    assert result["claim_description"] == "Broken windscreen"
