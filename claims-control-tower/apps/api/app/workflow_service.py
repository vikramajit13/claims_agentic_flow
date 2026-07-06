from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.db import ClaimDocumentRecord, ClaimRecord, WorkflowRunRecord, get_session
from app.enums import ClaimStatus, DocumentStatus, OcrStatus, WorkflowStatus, WorkflowStep
from app.observability import traceable
from app.schemas import WorkflowRunResponse, WorkflowStartRequest


def _now():
    return datetime.now(timezone.utc)


class WorkflowService:
    @traceable(name="start_mock_claim_workflow", run_type="chain")
    async def start_claim_workflow(self, claim_id: int, request: WorkflowStartRequest) -> WorkflowRunResponse:
        async with get_session() as session:
            claim = await session.get(ClaimRecord, claim_id)
            if claim is None:
                raise KeyError(claim_id)

            documents = (
                await session.execute(
                select(ClaimDocumentRecord).where(ClaimDocumentRecord.claim_id == claim_id)
                )
            ).scalars().all()

            hitl_required = settings.default_hitl_required if request.hitl_required is None else request.hitl_required
            if not documents:
                status = WorkflowStatus.WAITING_FOR_DOCUMENTS
                step = WorkflowStep.DOCUMENT_COLLECTION
                next_action = "Upload claim documents through the pre-signed S3 flow before starting the graph."
                claim.status = ClaimStatus.WAITING_FOR_DOCUMENTS.value
            elif any(document.upload_status == DocumentStatus.PENDING_UPLOAD.value for document in documents):
                status = WorkflowStatus.WAITING_FOR_DOCUMENTS
                step = WorkflowStep.DOCUMENT_COLLECTION
                next_action = "One or more documents have not been confirmed as uploaded yet."
                claim.status = ClaimStatus.WAITING_FOR_DOCUMENTS.value
            elif any(document.ocr_status == OcrStatus.PENDING.value for document in documents):
                status = WorkflowStatus.CREATED
                step = WorkflowStep.OCR_ENRICHMENT
                next_action = "OCR is pending for one or more documents. Finish enrichment before graph execution."
                claim.status = ClaimStatus.SUBMITTED.value
            elif hitl_required:
                status = WorkflowStatus.WAITING_FOR_HUMAN
                step = WorkflowStep.HUMAN_REVIEW
                next_action = "Human checkpoint reached before graph execution."
                claim.status = ClaimStatus.WAITING_FOR_HUMAN.value
            else:
                status = WorkflowStatus.READY_FOR_GRAPH
                step = WorkflowStep.GRAPH_BOOTSTRAP
                next_action = "Claim is ready for graph orchestration."
                claim.status = ClaimStatus.READY_FOR_GRAPH.value

            workflow = WorkflowRunRecord(
                claim_id=claim_id,
                status=status.value,
                current_step=step.value,
                hitl_required=hitl_required,
                next_action=next_action,
                notes=request.notes,
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(workflow)
            claim.updated_at = _now()
            await session.commit()
            await session.refresh(workflow)
            return WorkflowRunResponse(
                id=workflow.id,
                claim_id=workflow.claim_id,
                status=WorkflowStatus(workflow.status),
                current_step=WorkflowStep(workflow.current_step),
                hitl_required=workflow.hitl_required,
                next_action=workflow.next_action,
                notes=workflow.notes,
                created_at=workflow.created_at.isoformat(),
                updated_at=workflow.updated_at.isoformat(),
            )
