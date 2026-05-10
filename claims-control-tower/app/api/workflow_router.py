from fastapi import APIRouter, HTTPException

from app.schemas.workflow_schema import WorkflowExecutionResponse, WorkflowPauseRequest, WorkflowRunDetail
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1", tags=["workflows"])
workflow_service = WorkflowService()


@router.get("/workflows")
def get_workflows():
    return workflow_service.get_all_workflows()


@router.post("/claims/{claim_id}/workflow-runs", response_model=WorkflowExecutionResponse)
def start_claim_workflow(claim_id: int):
    try:
        return workflow_service.start_claim_workflow(claim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc


@router.post("/workflow-runs/{workflow_run_id}/execute", response_model=WorkflowExecutionResponse)
def execute_workflow_run(workflow_run_id: int):
    try:
        return workflow_service.execute(workflow_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Workflow run not found") from exc


@router.post("/workflow-runs/{workflow_run_id}/pause", response_model=WorkflowExecutionResponse)
def pause_workflow(workflow_run_id: int, request: WorkflowPauseRequest):
    try:
        return workflow_service.pause_workflow(workflow_run_id, request.reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Workflow run not found") from exc


@router.post("/workflow-runs/{workflow_run_id}/resume", response_model=WorkflowExecutionResponse)
def resume_workflow(workflow_run_id: int):
    try:
        return workflow_service.resume_workflow(workflow_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Workflow run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/workflow-runs/{workflow_run_id}", response_model=WorkflowRunDetail)
def get_workflow_run(workflow_run_id: int):
    try:
        return workflow_service.get_workflow_run(workflow_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Workflow run not found") from exc


@router.get("/workflow-runs/{workflow_run_id}/events")
def get_workflow_run_events(workflow_run_id: int):
    return workflow_service.get_workflow_run_events(workflow_run_id)
