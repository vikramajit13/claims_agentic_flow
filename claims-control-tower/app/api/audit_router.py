
from fastapi import APIRouter, Depends
from app.services.workflow_service import WorkflowService   

router = APIRouter(
    prefix="/v1",
    tags=["audit"]
)       

@router.get("/claims/{claim_id}/audit")
async def get_claim_audit(claim_id: int):
    return await WorkflowService.get_claim_audit(claim_id)