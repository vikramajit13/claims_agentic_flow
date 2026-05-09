from fastapi import APIRouter, HTTPException

from app.schemas.claim_schema import ClaimCreateRequest, ClaimResponse
from app.services.audit_service import AuditService
from app.services.claim_service import ClaimService

router = APIRouter(prefix="/v1/claims", tags=["claims"])
claim_service = ClaimService()
audit_service = AuditService()


@router.get("", response_model=list[ClaimResponse])
def get_claims():
    claims = claim_service.list_claims()
    return [claim_service.get_claim_response(claim.id) for claim in claims]


@router.post("", response_model=ClaimResponse)
def create_claim(claim: ClaimCreateRequest):
    return claim_service.submit_claim(claim)


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: int):
    try:
        return claim_service.get_claim_response(claim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc


@router.get("/{claim_id}/audit")
def get_claim_audit(claim_id: int):
    return audit_service.get_claim_audit(claim_id)
