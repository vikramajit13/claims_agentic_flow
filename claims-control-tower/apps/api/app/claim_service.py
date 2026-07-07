from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.db import ClaimDocumentRecord, ClaimRecord, get_session
from app.document_intelligence_service import DocumentIntelligenceOrchestrator
from app.enums import ClaimStatus, DocumentStatus, OcrStatus
from app.observability import traceable
from app.ocr_service import OCRService
from app.ocr_queue_service import OcrQueueService
from app.s3_service import S3Service
from app.schemas import (
    ClaimCreateRequest,
    ClaimDocumentResponse,
    ClaimResponse,
    DocumentUploadCompleteRequest,
    DocumentPresignRequest,
    DocumentPresignResponse,
)
from app.vector_service import VectorService


def _now():
    return datetime.now(timezone.utc)


class ClaimService:
    def __init__(self) -> None:
        self.s3_service = S3Service()
        self.ocr_service = OCRService()
        self.ocr_queue_service = OcrQueueService()
        self.document_intelligence_service = DocumentIntelligenceOrchestrator()
        self.vector_service = VectorService()

    @traceable(name="create_claim", run_type="chain")
    async def create_claim(self, request: ClaimCreateRequest) -> ClaimResponse:
        async with get_session() as session:
            record = ClaimRecord(
                claim_number=request.claim_number,
                customer_id=request.customer_id,
                claim_type=request.claim_type,
                description=request.description,
                incident_date=request.incident_date,
                claim_amount=request.claim_amount,
                status=ClaimStatus.DRAFT.value,
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return await self._claim_response(session, record)

    async def list_claims(self) -> list[ClaimResponse]:
        async with get_session() as session:
            claims = (await session.execute(select(ClaimRecord).order_by(ClaimRecord.id))).scalars().all()
            return [await self._claim_response(session, claim) for claim in claims]

    async def get_claim(self, claim_id: int) -> ClaimResponse:
        async with get_session() as session:
            claim = await session.get(ClaimRecord, claim_id)
            if claim is None:
                raise KeyError(claim_id)
            return await self._claim_response(session, claim)

    @traceable(name="create_document_presign", run_type="chain")
    async def create_document_presign(self, claim_id: int, request: DocumentPresignRequest) -> DocumentPresignResponse:
        async with get_session() as session:
            claim = await session.get(ClaimRecord, claim_id)
            if claim is None:
                raise KeyError(claim_id)

            s3_uri, bucket, key = self.s3_service.build_object_location(claim_id, request.file_name)
            document = ClaimDocumentRecord(
                claim_id=claim.id,
                file_name=request.file_name,
                content_type=request.content_type,
                s3_uri=s3_uri,
                s3_bucket=bucket,
                s3_key=key,
                upload_status=DocumentStatus.PENDING_UPLOAD.value,
                ocr_requested=request.run_ocr,
                ocr_status=OcrStatus.PENDING.value if request.run_ocr else OcrStatus.NOT_REQUESTED.value,
                ocr_job_id=None,
                ocr_error=None,
                ocr_text=None,
                embedding_vector=None,
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(document)
            await session.flush()

            upload_url, upload_headers = self.s3_service.create_presigned_upload(
                bucket=bucket,
                key=key,
                content_type=request.content_type,
                metadata={
                    "document-id": str(document.id),
                    "claim-id": str(claim.id),
                    "run-ocr": str(request.run_ocr).lower(),
                },
            )

            claim.status = ClaimStatus.SUBMITTED.value
            claim.updated_at = _now()
            await session.commit()
            await session.refresh(document)

            return DocumentPresignResponse(
                document_id=document.id,
                upload_url=upload_url,
                upload_headers=upload_headers,
                s3_uri=s3_uri,
                s3_bucket=bucket,
                s3_key=key,
                expires_in_seconds=settings.s3_presign_expiry_seconds,
            )

    @traceable(name="complete_document_upload", run_type="chain")
    async def complete_document_upload(
        self,
        claim_id: int,
        document_id: int,
        request: DocumentUploadCompleteRequest,
    ) -> ClaimDocumentResponse:
        async with get_session() as session:
            claim = await session.get(ClaimRecord, claim_id)
            if claim is None:
                raise KeyError(claim_id)

            document = await session.get(ClaimDocumentRecord, document_id)
            if document is None or document.claim_id != claim_id:
                raise KeyError(document_id)

            if not self.s3_service.object_exists(bucket=document.s3_bucket, key=document.s3_key):
                raise FileNotFoundError(document.s3_uri)

            document.upload_status = DocumentStatus.UPLOADED.value
            document.updated_at = _now()

            trigger_ocr = document.ocr_requested if request.trigger_ocr is None else request.trigger_ocr
            if trigger_ocr and document.ocr_requested:
                if settings.use_mock_ocr:
                    ocr_status, textract_result = self.ocr_service.extract_from_s3(
                        s3_uri=document.s3_uri,
                        file_name=document.file_name,
                    )
                    intelligence_result = self.document_intelligence_service.process(
                        file_name=document.file_name,
                        textract_result=textract_result,
                    )
                    document.ocr_status = ocr_status.value
                    document.ocr_text = intelligence_result.raw_text
                    document.normalized_text = intelligence_result.normalized_text
                    document.textract_blocks = intelligence_result.textract_blocks
                    document.validation_results = intelligence_result.validation_results
                    document.document_classification = intelligence_result.document_classification
                    document.extracted_fields = intelligence_result.extracted_fields
                    document.quality_assessment = intelligence_result.quality_assessment
                    document.embedding_vector = self.vector_service.embed_text(intelligence_result.normalized_text)
                    document.upload_status = DocumentStatus.OCR_COMPLETED.value
                    document.ocr_job_id = None
                    document.ocr_error = None
                elif settings.use_mock_s3:
                    document.ocr_job_id = self.ocr_queue_service.enqueue_document(
                        document_id=document.id,
                        claim_id=claim_id,
                        s3_bucket=document.s3_bucket,
                        s3_key=document.s3_key,
                        s3_uri=document.s3_uri,
                    )
                    document.upload_status = DocumentStatus.OCR_QUEUED.value
                    document.ocr_status = OcrStatus.PENDING.value
                    document.ocr_error = None
                else:
                    document.upload_status = DocumentStatus.UPLOADED.value
                    document.ocr_status = OcrStatus.PENDING.value
                    document.ocr_job_id = None
                    document.ocr_error = None
            else:
                document.ocr_status = OcrStatus.NOT_REQUESTED.value
                document.ocr_job_id = None
                document.ocr_error = None

            claim.status = ClaimStatus.SUBMITTED.value
            claim.updated_at = _now()
            await session.commit()
            await session.refresh(document)
            return self._document_response(document)

    async def _claim_response(self, session, claim: ClaimRecord) -> ClaimResponse:
        documents = (
            await session.execute(
                select(ClaimDocumentRecord).where(ClaimDocumentRecord.claim_id == claim.id).order_by(ClaimDocumentRecord.id)
            )
        ).scalars().all()
        return ClaimResponse(
            id=claim.id,
            claim_number=claim.claim_number,
            customer_id=claim.customer_id,
            claim_type=claim.claim_type,
            description=claim.description,
            incident_date=claim.incident_date,
            claim_amount=claim.claim_amount,
            status=ClaimStatus(claim.status),
            documents=[self._document_response(document) for document in documents],
            created_at=claim.created_at.isoformat(),
            updated_at=claim.updated_at.isoformat(),
        )

    def _document_response(self, document: ClaimDocumentRecord) -> ClaimDocumentResponse:
        return ClaimDocumentResponse(
            id=document.id,
            file_name=document.file_name,
            content_type=document.content_type,
            s3_uri=document.s3_uri,
            s3_bucket=document.s3_bucket,
            s3_key=document.s3_key,
            upload_status=DocumentStatus(document.upload_status),
            ocr_requested=document.ocr_requested,
            ocr_status=OcrStatus(document.ocr_status),
            ocr_job_id=document.ocr_job_id,
            ocr_error=document.ocr_error,
            ocr_text=document.ocr_text,
            normalized_text=document.normalized_text,
            validation_results=document.validation_results,
            document_classification=document.document_classification,
            extracted_fields=document.extracted_fields,
            quality_assessment=document.quality_assessment,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )
