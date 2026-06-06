from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langsmith import Client, evaluate

from app.agent.state import claims_review_graph
from app.database import get_store
from app.schemas.claim_schema import ClaimCreateRequest, DocumentUpload
from app.services.case_packet import CasePacketBuilder
from app.services.claim_service import ClaimService
from app.services.policy_admin_adapter import PolicyAdminAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_NAME = "claims-review-agent-evals"


def _load_examples() -> list[dict[str, Any]]:
    return json.loads((PROJECT_ROOT / "evals" / "claims_review_examples.json").read_text())


def _ensure_dataset(client: Client) -> str:
    for dataset in client.list_datasets(dataset_name=DATASET_NAME):
        return dataset.id

    dataset = client.create_dataset(dataset_name=DATASET_NAME, description="Offline regression evals for claims review agent")
    examples = _load_examples()
    client.create_examples(
        dataset_id=dataset.id,
        inputs=[{"claim_request": example["claim_request"]} for example in examples],
        outputs=[example["reference_outputs"] for example in examples],
    )
    return dataset.id


def _build_case_packet(claim_request_payload: dict[str, Any]):
    get_store().reset()
    claim_service = ClaimService()
    policy_adapter = PolicyAdminAdapter()
    case_packet_builder = CasePacketBuilder()

    documents = [
        DocumentUpload(**document_payload)
        for document_payload in claim_request_payload.get("documents", [])
    ]
    created = claim_service.submit_claim(
        ClaimCreateRequest(
            **{**claim_request_payload, "documents": documents}
        )
    )
    claim = claim_service.get_claim(created.claim.id)
    policy = policy_adapter.get_policy(claim.policy_id)
    return case_packet_builder.build(
        claim=claim,
        policy=policy,
        documents=claim_service.get_claim_documents(claim.id),
        coverage_result={"is_valid": True, "reasons": []},
        evidence_result={"is_valid": True, "reasons": [], "missing_documents": []},
        risk_result={"risk_score": 10, "risk_level": "LOW", "risk_factors": []},
        guardrail_results=[],
        recommendation={"recommendation": "APPROVE", "reason": "Eval execution"},
        claim_history_summary={"recent_30_day_claim_count": 0, "last_12_month_claim_count": 0},
        workflow_run_id=9999,
    )


def run_claims_review_graph_target(inputs: dict[str, Any]) -> dict[str, Any]:
    case_packet = _build_case_packet(inputs["claim_request"])
    graph_state = claims_review_graph.invoke({"case_packet": case_packet})
    recommended_next_action = graph_state.get("recommended_next_action")
    risk_analysis = graph_state.get("risk_analysis")
    previous_tool_calls = graph_state.get("previous_tool_calls", [])
    tool_names = []
    for call in previous_tool_calls:
        if isinstance(call, dict):
            tool_names.append(call.get("tool_name"))
        else:
            tool_names.append(getattr(call, "tool_name", None))

    next_action = None
    requires_human_review = None
    if recommended_next_action:
        if isinstance(recommended_next_action, dict):
            next_action = recommended_next_action.get("next_action")
            requires_human_review = recommended_next_action.get("requires_human_review")
        else:
            next_action = recommended_next_action.next_action
            requires_human_review = recommended_next_action.requires_human_review

    risk_level = None
    if risk_analysis:
        if isinstance(risk_analysis, dict):
            risk_level = risk_analysis.get("risk_level")
        else:
            risk_level = risk_analysis.risk_level

    return {
        "next_action": next_action,
        "risk_level": risk_level,
        "requires_human_review": requires_human_review,
        "tool_names": [tool_name for tool_name in tool_names if tool_name],
    }


def next_action_evaluator(*, outputs: dict, reference_outputs: dict) -> dict:
    expected = reference_outputs["next_action"]
    actual = outputs.get("next_action")
    return {"key": "next_action_match", "score": actual == expected}


def risk_level_evaluator(*, outputs: dict, reference_outputs: dict) -> dict:
    expected = reference_outputs["risk_level"]
    actual = outputs.get("risk_level")
    return {"key": "risk_level_match", "score": actual == expected}


def human_review_evaluator(*, outputs: dict, reference_outputs: dict) -> dict:
    expected = reference_outputs["requires_human_review"]
    actual = outputs.get("requires_human_review")
    return {"key": "requires_human_review_match", "score": actual == expected}


def tool_usage_evaluator(*, outputs: dict, reference_outputs: dict) -> dict:
    expected_tools = set(reference_outputs.get("expected_tools", []))
    actual_tools = set(outputs.get("tool_names", []))
    return {"key": "expected_tools_used", "score": expected_tools.issubset(actual_tools)}


def main() -> None:
    client = Client()
    dataset_id = _ensure_dataset(client)
    evaluate(
        run_claims_review_graph_target,
        data=dataset_id,
        evaluators=[
            next_action_evaluator,
            risk_level_evaluator,
            human_review_evaluator,
            tool_usage_evaluator,
        ],
        experiment_prefix="claims-review-agent",
    )


if __name__ == "__main__":
    main()
