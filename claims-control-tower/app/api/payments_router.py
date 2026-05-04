
from fastapi import APIRouter, Depends
from app.services.workflow_service import WorkflowService


router = APIRouter(
    prefix="/v1",
    tags=["payments"]
)       

@router.get("/payment-instructions")
async def get_payment_instructions():
    return await WorkflowService.get_all_payment_instructions()

@router.get("/payment-instructions/{payment_instruction_id}")
async def get_payment_instruction(payment_instruction_id: int):
    return await WorkflowService.get_payment_instruction(payment_instruction_id)

@router.post("/claims/{claim_id}/payment-instructions")
async def create_payment_instruction(claim_id: int, payment_instruction: dict):
    return await WorkflowService.create_payment_instruction(claim_id, payment_instruction)
