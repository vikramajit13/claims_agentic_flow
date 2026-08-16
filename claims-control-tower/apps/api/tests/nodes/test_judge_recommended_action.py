import asyncio

from langchain_core.messages import AIMessage

from app.graph.state import ClaimGraphState
from app.nodes.judge_recommended_action import judge_recommended_action


class _FakeActionJudgeClient:
    def create_json_response(self, *, system_prompt: str, user_prompt: str, model: str) -> dict:
        assert "Selected actions" in user_prompt
        assert model
        return {
            "approved": False,
            "rationale": "Need human review for this risk level.",
            "missing_actions": ["CREATE_HUMAN_REVIEW_TASK"],
            "unnecessary_actions": ["PROCEED_TO_PAYMENT_GUARDRAILS"],
        }


def test_action_judge_applies_blocking_verdict_for_high_risk():
    state = ClaimGraphState(
        claim_id=31,
        risk_score=88,
        risk_level="HIGH",
        messages=[
            AIMessage(
                content="Action plan",
                tool_calls=[
                    {
                        "name": "recommend_proceed_to_payment_action",
                        "args": {"reason": "safe", "priority": 70, "confidence": 0.8},
                        "id": "tool-1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    )

    result = asyncio.run(judge_recommended_action(state, llm_client=_FakeActionJudgeClient()))

    assert result["action_selection_judgment"]["mode"] == "blocking"
    assert result["action_selection_judgment"]["applied"] is True
    tool_names = [tool["name"] for tool in result["messages"][0].tool_calls]
    assert "recommend_human_review_action" in tool_names
    assert "recommend_proceed_to_payment_action" not in tool_names


def test_action_judge_records_advisory_verdict_for_low_risk():
    state = ClaimGraphState(
        claim_id=32,
        risk_score=18,
        risk_level="LOW",
        messages=[
            AIMessage(
                content="Action plan",
                tool_calls=[
                    {
                        "name": "recommend_proceed_to_payment_action",
                        "args": {"reason": "safe", "priority": 70, "confidence": 0.8},
                        "id": "tool-2",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    )

    result = asyncio.run(judge_recommended_action(state, llm_client=_FakeActionJudgeClient()))

    assert result["action_selection_judgment"]["mode"] == "advisory"
    assert result["action_selection_judgment"]["applied"] is False
    tool_names = [tool["name"] for tool in result["messages"][0].tool_calls]
    assert tool_names == ["recommend_proceed_to_payment_action"]
