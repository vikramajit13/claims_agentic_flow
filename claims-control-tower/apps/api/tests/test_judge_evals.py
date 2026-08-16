import asyncio
import json
from pathlib import Path

from langchain_core.messages import AIMessage

from app.graph.state import ClaimGraphState
from app.nodes.judge_tool_selection import judge_tool_selection


class _EvalJudgeClient:
    def __init__(self, response: dict):
        self.response = response

    def judge_tool_selection(self, *, system_prompt: str, user_prompt: str) -> dict:
        assert system_prompt
        assert user_prompt
        return self.response


def _load_cases() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "evals" / "judge_eval_cases.json"
    return json.loads(path.read_text())


def _tool_call(name: str, claim_id: int) -> dict:
    args_map = {
        "get_claim_history": {"customer_id": 1001, "lookback_months": 12, "exclude_claim_id": claim_id},
        "get_document_metadata": {"claim_id": claim_id},
        "get_customer_risk_overview": {"customer_id": 1001, "exclude_claim_id": claim_id},
    }
    return {"name": name, "args": args_map[name], "id": f"tool-{name}", "type": "tool_call"}


def test_judge_eval_cases():
    for case in _load_cases():
        state = ClaimGraphState(
            claim_id=401,
            customer_id=1001,
            risk_score=case["risk_score"],
            risk_level=case["risk_level"],
            selected_investigation_graph=case["selected_graph"],
            selected_investigation_reason="eval",
            investigation_plan=[{"graph_name": case["selected_graph"], "reason": "eval"}],
            messages=[AIMessage(content="Investigating", tool_calls=[_tool_call(name, 401) for name in case["selected_tools"]])],
        )

        result = asyncio.run(judge_tool_selection(state, llm_client=_EvalJudgeClient(case["judge_response"])))

        assert result["tool_selection_judgment"]["mode"] == case["expected"]["mode"], case["name"]
        assert result["tool_selection_judgment"]["applied"] is case["expected"]["applied"], case["name"]
        tool_names = [tool["name"] for tool in result["messages"][0].tool_calls]
        for expected_name in case["expected"]["tool_names_include"]:
            assert expected_name in tool_names, case["name"]
