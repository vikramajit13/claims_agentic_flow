import asyncio

from langchain_core.messages import AIMessage

from app.graph.state import ClaimGraphState
from app.nodes.judge_tool_selection import judge_tool_selection


class _FakeJudgeClient:
    def judge_tool_selection(self, *, system_prompt: str, user_prompt: str) -> dict:
        assert "customer_history_graph" in user_prompt
        assert "get_claim_history" in user_prompt
        return {
            "approved": False,
            "rationale": "Need the aggregate customer view as well.",
            "missing_tools": ["get_customer_risk_overview"],
            "unnecessary_tools": [],
        }


class _FakeFailingJudgeClient:
    def judge_tool_selection(self, *, system_prompt: str, user_prompt: str) -> dict:
        del system_prompt
        del user_prompt
        raise RuntimeError("judge unavailable")


def test_judge_tool_selection_adds_missing_safe_tool(monkeypatch):
    del monkeypatch

    state = ClaimGraphState(
        claim_id=22,
        customer_id=1001,
        risk_score=85,
        risk_level="HIGH",
        selected_investigation_graph="customer_history_graph",
        selected_investigation_reason="High risk customer history review.",
        investigation_plan=[{"graph_name": "customer_history_graph", "reason": "history first"}],
        messages=[
            AIMessage(
                content="Investigating",
                tool_calls=[
                    {
                        "name": "get_claim_history",
                        "args": {"customer_id": 1001, "lookback_months": 12, "exclude_claim_id": 22},
                        "id": "tool-1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    )

    result = asyncio.run(judge_tool_selection(state, llm_client=_FakeJudgeClient()))

    assert result["tool_selection_judgment"]["approved"] is False
    assert "get_customer_risk_overview" in result["tool_selection_judgment"]["added_tools"]
    revised_tool_names = [tool["name"] for tool in result["messages"][0].tool_calls]
    assert revised_tool_names == ["get_claim_history", "get_customer_risk_overview"]


def test_judge_tool_selection_falls_back_gracefully(monkeypatch):
    del monkeypatch

    state = ClaimGraphState(
        claim_id=23,
        customer_id=1001,
        selected_investigation_graph="customer_history_graph",
        messages=[
            AIMessage(
                content="Investigating",
                tool_calls=[
                    {
                        "name": "get_claim_history",
                        "args": {"customer_id": 1001, "lookback_months": 12, "exclude_claim_id": 23},
                        "id": "tool-2",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    )

    result = asyncio.run(judge_tool_selection(state, llm_client=_FakeFailingJudgeClient()))

    assert result["tool_selection_judgment"]["approved"] is True
    assert "failed" in result["investigation_notes"][-1].lower()
