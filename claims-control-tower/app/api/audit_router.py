from fastapi import APIRouter

from app.services.audit_service import AuditService

router = APIRouter(prefix="/v1/audit", tags=["audit"])
audit_service = AuditService()


@router.get("/claims/{claim_id}")
def get_claim_audit(claim_id: int):
    return audit_service.get_claim_audit(claim_id)
