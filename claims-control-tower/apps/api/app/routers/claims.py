from fastapi import APIRouter, HTTPException

from app.claim_service import ClaimService
from app.schemas import (
    ClaimCreateRequest,
    ClaimDocumentResponse,
    ClaimResponse,
    DocumentPresignRequest,
    DocumentPresignResponse,
    DocumentUploadCompleteRequest,
)

router = APIRouter(prefix="/v1/claims", tags=["claims"])
claim_service = ClaimService()


@router.get("", response_model=list[ClaimResponse])
async def list_claims():
    return await claim_service.list_claims()


@router.post("", response_model=ClaimResponse)
async def create_claim(request: ClaimCreateRequest):
    return await claim_service.create_claim(request)


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: int):
    try:
        return await claim_service.get_claim(claim_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc


@router.post("/{claim_id}/documents/presign", response_model=DocumentPresignResponse)
async def create_document_presign(claim_id: int, request: DocumentPresignRequest):
    try:
        return await claim_service.create_document_presign(claim_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim not found") from exc


@router.post("/{claim_id}/documents/{document_id}/complete-upload", response_model=ClaimDocumentResponse)
async def complete_document_upload(claim_id: int, document_id: int, request: DocumentUploadCompleteRequest):
    try:
        return await claim_service.complete_document_upload(claim_id, document_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Claim or document not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=f"Document not found in S3: {exc.args[0]}") from exc

