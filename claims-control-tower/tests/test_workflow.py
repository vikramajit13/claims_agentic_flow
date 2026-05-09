from app.models.claim import ClaimStatus
from app.models.claim_document import DocumentType
from app.models.workflow_run import WorkflowRunStatus
from app.schemas.claim_schema import ClaimCreateRequest, DocumentUpload
from app.schemas.human_task_schema import HumanTaskDecisionRequest
from app.services.claim_service import ClaimService
from app.services.workflow_service import WorkflowService


def test_workflow_auto_approval_creates_payment_instruction():
    claim_service = ClaimService()
    workflow_service = WorkflowService()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="TEST-AUTO-001",
            customer_id=100,
            policy_id=1,
            claim_type="motor",
            claim_amount=4200,
            incident_date="2026-03-05",
            description="Minor collision with standard evidence attached",
            documents=[
                DocumentUpload(
                    document_type=DocumentType.PHOTO,
                    file_name="photo.jpg",
                    storage_url="s3://claims/photo.jpg",
                ),
                DocumentUpload(
                    document_type=DocumentType.REPAIR_ESTIMATE,
                    file_name="estimate.pdf",
                    storage_url="s3://claims/estimate.pdf",
                ),
            ],
        )
    )

    result = workflow_service.start_claim_workflow(created.claim.id)

    assert result.workflow_run.status == WorkflowRunStatus.COMPLETED
    assert result.recommendation is not None
    assert result.recommendation.recommendation == "APPROVE"
    assert result.payment_instruction_id is not None
    assert claim_service.get_claim(created.claim.id).status == ClaimStatus.PAYMENT_READY


def test_workflow_human_review_resume_creates_payment_instruction():
    claim_service = ClaimService()
    workflow_service = WorkflowService()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="TEST-HUMAN-001",
            customer_id=100,
            policy_id=1,
            claim_type="theft",
            claim_amount=9000,
            incident_date="2026-01-03",
            description="Urgent cash reimbursement needed after theft",
            documents=[
                DocumentUpload(
                    document_type=DocumentType.POLICE_REPORT,
                    file_name="police.pdf",
                    storage_url="s3://claims/police.pdf",
                )
            ],
        )
    )

    first_result = workflow_service.start_claim_workflow(created.claim.id)

    assert first_result.workflow_run.status == WorkflowRunStatus.WAITING_FOR_HUMAN
    assert first_result.human_task_id is not None

    _, resumed_result = workflow_service.complete_human_task(
        first_result.human_task_id,
        HumanTaskDecisionRequest(
            reviewer_id="reviewer-1",
            decision="APPROVE",
            decision_notes="Approved after manual review",
        ),
    )

    assert resumed_result.workflow_run.status == WorkflowRunStatus.COMPLETED
    assert resumed_result.payment_instruction_id is not None
    assert claim_service.get_claim(created.claim.id).status == ClaimStatus.PAYMENT_READY
