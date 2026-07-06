from fastapi import APIRouter, HTTPException

from app.schemas import WorkflowRunResponse, WorkflowStartRequest
from app.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])
workflow_service = WorkflowService()


@router.post("/claims/{claim_id}/start", response_model=WorkflowRunResponse)
async def start_workflow(claim_id: int, request: WorkflowStartRequest | None = None):
    try:
        return await workflow_service.start_claim_workflow(claim_id, request or WorkflowStartRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc
