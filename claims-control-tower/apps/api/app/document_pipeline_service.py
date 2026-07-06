from __future__ import annotations

from sqlalchemy import select

from app.config import settings
from app.db import ClaimDocumentRecord, ClaimRecord, get_session
from app.enums import ClaimStatus, DocumentStatus, OcrStatus
from app.observability import traceable
from app.ocr_queue_service import OcrQueueService
from app.ocr_service import OCRService
from app.vector_service import VectorService


class DocumentPipelineService:
    def __init__(self) -> None:
        self.ocr_queue_service = OcrQueueService()
        self.ocr_service = OCRService()
        self.vector_service = VectorService()

    @traceable(name="handle_s3_object_created", run_type="chain")
    async def handle_s3_object_created(self, *, bucket: str, key: str) -> dict:
        async with get_session() as session:
            document = (
                await session.execute(
                    select(ClaimDocumentRecord).where(
                        ClaimDocumentRecord.s3_bucket == bucket,
                        ClaimDocumentRecord.s3_key == key,
                    )
                )
            ).scalar_one_or_none()

            if document is None:
                return {
                    "status": "ignored",
                    "reason": "document_not_found",
                    "s3_bucket": bucket,
                    "s3_key": key,
                }

            claim = await session.get(ClaimRecord, document.claim_id)
            document.upload_status = DocumentStatus.UPLOADED.value

            if document.ocr_requested:
                document.ocr_job_id = self.ocr_queue_service.enqueue_document(
                    document_id=document.id,
                    claim_id=document.claim_id,
                    s3_bucket=document.s3_bucket,
                    s3_key=document.s3_key,
                    s3_uri=document.s3_uri,
                )
                document.upload_status = DocumentStatus.OCR_QUEUED.value
                document.ocr_status = OcrStatus.PENDING.value
                document.ocr_error = None
            else:
                document.ocr_status = OcrStatus.NOT_REQUESTED.value
                document.ocr_job_id = None
                document.ocr_error = None

            if claim is not None:
                claim.status = ClaimStatus.SUBMITTED.value

            await session.commit()
            await session.refresh(document)

            return {
                "status": "processed",
                "document_id": document.id,
                "claim_id": document.claim_id,
                "upload_status": document.upload_status,
                "ocr_status": document.ocr_status,
                "ocr_job_id": document.ocr_job_id,
            }

    @traceable(name="mark_document_uploaded", run_type="chain")
    async def mark_document_uploaded(
        self,
        *,
        document_id: int,
        claim_id: int,
        s3_bucket: str,
        s3_key: str,
        queued_for_ocr: bool,
        ocr_job_id: str | None,
    ) -> dict:
        async with get_session() as session:
            document = await session.get(ClaimDocumentRecord, document_id)
            if document is None or document.claim_id != claim_id:
                return {
                    "status": "ignored",
                    "reason": "document_not_found",
                    "document_id": document_id,
                    "claim_id": claim_id,
                }

            claim = await session.get(ClaimRecord, claim_id)

            document.s3_bucket = s3_bucket
            document.s3_key = s3_key
            document.upload_status = (
                DocumentStatus.OCR_QUEUED.value if queued_for_ocr and document.ocr_requested else DocumentStatus.UPLOADED.value
            )
            document.ocr_status = (
                OcrStatus.PENDING.value if queued_for_ocr and document.ocr_requested else OcrStatus.NOT_REQUESTED.value
            )
            document.ocr_job_id = ocr_job_id if queued_for_ocr and document.ocr_requested else None
            document.ocr_error = None

            if claim is not None:
                claim.status = ClaimStatus.SUBMITTED.value

            await session.commit()
            await session.refresh(document)

            return {
                "status": "processed",
                "document_id": document.id,
                "claim_id": document.claim_id,
                "upload_status": document.upload_status,
                "ocr_status": document.ocr_status,
                "ocr_job_id": document.ocr_job_id,
            }

    @traceable(name="process_ocr_job", run_type="chain")
    async def process_ocr_job(self, *, document_id: int) -> dict:
        async with get_session() as session:
            document = await session.get(ClaimDocumentRecord, document_id)
            if document is None:
                return {
                    "status": "ignored",
                    "reason": "document_not_found",
                    "document_id": document_id,
                }

            try:
                ocr_status, ocr_text = self.ocr_service.extract_from_s3(
                    s3_uri=document.s3_uri,
                    file_name=document.file_name,
                )
                document.ocr_status = ocr_status.value
                document.ocr_text = ocr_text
                document.embedding_vector = self.vector_service.embed_text(ocr_text)
                document.upload_status = DocumentStatus.OCR_COMPLETED.value
                document.ocr_error = None
            except Exception as exc:  # pragma: no cover - defensive branch
                document.ocr_status = OcrStatus.FAILED.value
                document.ocr_error = str(exc)
                await session.commit()
                raise

            await session.commit()
            await session.refresh(document)

            return {
                "status": "processed",
                "document_id": document.id,
                "claim_id": document.claim_id,
                "upload_status": document.upload_status,
                "ocr_status": document.ocr_status,
            }
