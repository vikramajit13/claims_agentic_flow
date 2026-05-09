from fastapi import APIRouter, HTTPException

from app.schemas.payment_schema import PaymentInstructionResponse
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/payment-instructions", tags=["payments"])
workflow_service = WorkflowService()


@router.get("")
def get_payment_instructions():
    return workflow_service.get_all_payment_instructions()


@router.get("/{payment_instruction_id}", response_model=PaymentInstructionResponse)
def get_payment_instruction(payment_instruction_id: int):
    try:
        return workflow_service.get_payment_instruction(payment_instruction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Payment instruction not found") from exc
