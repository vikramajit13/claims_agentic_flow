from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.investigation_schema import ToolExecutionRecord
from app.services.observability import traceable


@traceable(name="merge_tool_result_node", run_type="chain")
def merge_tool_result_node(state: ClaimreviewState):
    latest_tool_result = state.latest_tool_result
    if latest_tool_result is None:
        return {}
    if isinstance(latest_tool_result, dict):
        latest_tool_result = ToolExecutionRecord(**latest_tool_result)

    tool_results = dict(state.tool_results)
    tool_results[latest_tool_result.tool_name] = latest_tool_result.result
    previous_tool_calls = list(state.previous_tool_calls)
    previous_tool_calls.append(latest_tool_result)
    return {
        "tool_results": tool_results,
        "previous_tool_calls": [call.dict() if hasattr(call, "dict") else call for call in previous_tool_calls],
        "latest_tool_result": None,
        "selected_tool_decision": None,
    }
