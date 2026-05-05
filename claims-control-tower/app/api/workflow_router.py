
from fastapi import APIRouter, Depends
from app.services.workflow_service import WorkflowService

router = APIRouter(
    prefix="/v1",
    tags=["workflows"]
)

@router.get("/workflows")
async def get_workflows():
    return await WorkflowService.get_all_workflows()

@router.post("/workflows")
async def create_workflow(workflow: dict):
    return await WorkflowService.create_workflow(workflow)


@router.post("/claims/{claim_id}/workflow/execute")
async def start_claim_workflow(claim_id: int):
    return await WorkflowService.start_claim_workflow(claim_id)

@router.post("/workflow-runs/{workflow_run_id}/execute")
async def execute_workflow_run(workflow_run_id: int):
    return await WorkflowService.execute_workflow_run(workflow_run_id)

@router.get("/workflow-runs/{workflow_run_id}")
async def get_workflow_run(workflow_run_id: int):
    return await WorkflowService.get_workflow_run(workflow_run_id)

@router.get("/workflow-runs/{workflow_run_id}/events")
async def get_workflow_run_events(workflow_run_id: int):
    return await WorkflowService.get_workflow_run_events(workflow_run_id)