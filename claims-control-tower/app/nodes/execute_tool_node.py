from app.models.claims_workflow_state import ClaimreviewState
from app.schemas.investigation_schema import ToolDecision, ToolExecutionRecord
from app.services.observability import traceable
from app.tool.tools import invoke_safe_read_tool


@traceable(name="execute_tool_node", run_type="tool")
def execute_tool_node(state: ClaimreviewState):
    selected_tool_decision = state.selected_tool_decision
    if selected_tool_decision is not None and isinstance(selected_tool_decision, dict):
        selected_tool_decision = ToolDecision(**selected_tool_decision)
    if selected_tool_decision is None or not selected_tool_decision.selected_tool:
        return {"latest_tool_result": None}

    result = invoke_safe_read_tool(
        selected_tool_decision.selected_tool,
        selected_tool_decision.tool_arguments,
    )
    execution_record = ToolExecutionRecord(
        tool_name=selected_tool_decision.selected_tool,
        tool_arguments=selected_tool_decision.tool_arguments,
        reason=selected_tool_decision.reason,
        result=result,
    )
    return {"latest_tool_result": execution_record.dict()}
