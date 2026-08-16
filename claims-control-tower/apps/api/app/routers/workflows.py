from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    HumanReviewDecisionRequest,
    HumanReviewResponse,
    WorkflowTraceResponse,
    WorkflowRunResponse,
    WorkflowStartRequest,
)
from app.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])
workflow_service = WorkflowService()


@router.post("/claims/{claim_id}/start", response_model=WorkflowRunResponse)
async def start_workflow(claim_id: int, request: WorkflowStartRequest | None = None):
    try:
        return await workflow_service.start_claim_workflow(claim_id, request or WorkflowStartRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc


@router.get("/human-reviews/{review_id}", response_model=HumanReviewResponse)
async def get_human_review(review_id: int):
    try:
        return await workflow_service.get_human_review(review_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human review not found") from exc


@router.get("/human-reviews", response_model=list[HumanReviewResponse])
async def list_human_reviews(status: str | None = Query(default="pending")):
    return await workflow_service.list_human_reviews(status=status)


@router.post("/human-reviews/{review_id}/resume", response_model=HumanReviewResponse)
async def resume_human_review(review_id: int, request: HumanReviewDecisionRequest):
    try:
        return await workflow_service.resume_human_review(review_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human review not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/claims/{claim_id}/trace", response_model=WorkflowTraceResponse)
async def get_claim_trace(claim_id: int):
    return await workflow_service.get_claim_trace(claim_id)
