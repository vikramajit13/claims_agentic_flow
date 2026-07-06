from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.document_pipeline_service import DocumentPipelineService
from app.schemas import InternalProcessOcrRequest, InternalS3ObjectCreatedRequest

router = APIRouter(prefix="/internal", tags=["internal"])
document_pipeline_service = DocumentPipelineService()


def _verify_internal_token(token: str | None) -> None:
    if not settings.internal_service_token:
        raise HTTPException(status_code=503, detail="Internal service token is not configured")
    if token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="Invalid internal service token")


@router.post("/documents/s3-object-created")
async def handle_s3_object_created(
    request: InternalS3ObjectCreatedRequest,
    x_internal_token: str | None = Header(default=None),
):
    _verify_internal_token(x_internal_token)
    return await document_pipeline_service.mark_document_uploaded(
        document_id=request.document_id,
        claim_id=request.claim_id,
        s3_bucket=request.s3_bucket,
        s3_key=request.s3_key,
        queued_for_ocr=request.queued_for_ocr,
        ocr_job_id=request.ocr_job_id,
    )


@router.post("/documents/process-ocr")
async def process_ocr_document(
    request: InternalProcessOcrRequest,
    x_internal_token: str | None = Header(default=None),
):
    _verify_internal_token(x_internal_token)
    return await document_pipeline_service.process_ocr_job(document_id=request.document_id)
