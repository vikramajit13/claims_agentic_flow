from fastapi import APIRouter, HTTPException

from app.claim_service import ClaimService
from app.schemas import ClaimCreateRequest, ClaimResponse, DocumentPresignRequest, DocumentPresignResponse

router = APIRouter(prefix="/v1/claims", tags=["claims"])
claim_service = ClaimService()


@router.get("", response_model=list[ClaimResponse])
def list_claims():
    return claim_service.list_claims()


@router.post("", response_model=ClaimResponse)
def create_claim(request: ClaimCreateRequest):
    return claim_service.create_claim(request)


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: int):
    try:
        return claim_service.get_claim(claim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc


@router.post("/{claim_id}/documents/presign", response_model=DocumentPresignResponse)
def create_document_presign(claim_id: int, request: DocumentPresignRequest):
    try:
        return claim_service.create_document_presign(claim_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc
