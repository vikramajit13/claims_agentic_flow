from app.database import get_store
from app.models.claim import ClaimStatus
from app.models.claim_document import DocumentType
from app.models.workflow_run import WorkflowRunStatus
from app.schemas.claim_schema import ClaimCreateRequest, DocumentUpload
from app.schemas.human_task_schema import HumanTaskDecisionRequest
from app.services.claim_service import ClaimService
from app.services.human_task_service import HumanTaskService
from app.services.workflow_service import WorkflowService


def setup_function():
    get_store().reset()


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
            completed_by="reviewer-1",
            decision="APPROVE",
            decision_notes="Approved after manual review",
        ),
    )

    assert resumed_result.workflow_run.status == WorkflowRunStatus.COMPLETED
    assert resumed_result.payment_instruction_id is not None
    assert claim_service.get_claim(created.claim.id).status == ClaimStatus.PAYMENT_READY


def test_phase_2_suspicious_claim_pauses_with_payment_review_task():
    claim_service = ClaimService()
    workflow_service = WorkflowService()
    task_service = HumanTaskService()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="CLM-2026-001",
            customer_id=999,
            policy_id=4,
            claim_type="motor",
            claim_amount=4200,
            incident_date="2026-04-25",
            description="Rear bumper damage after accident",
            documents=[
                DocumentUpload(
                    document_type=DocumentType.INVOICE,
                    file_name="repair-invoice.pdf",
                    storage_url="s3://claims/repair-invoice.pdf",
                    document_metadata={
                        "invoice_date": "2026-04-20",
                        "invoice_amount": 4200,
                        "vendor_name": "ABC Repairs",
                    },
                ),
                DocumentUpload(
                    document_type=DocumentType.PHOTO,
                    file_name="damage-photo.jpg",
                    storage_url="s3://claims/damage-photo.jpg",
                ),
                DocumentUpload(
                    document_type=DocumentType.REPAIR_ESTIMATE,
                    file_name="repair-estimate.pdf",
                    storage_url="s3://claims/repair-estimate.pdf",
                ),
            ],
        )
    )

    result = workflow_service.start_claim_workflow(created.claim.id)

    assert result.workflow_run.status == WorkflowRunStatus.WAITING_FOR_HUMAN
    assert result.claim_status == ClaimStatus.PENDING_HUMAN_REVIEW.value
    assert result.human_task_id is not None
    assert result.recommendation is not None
    assert result.recommendation.recommendation == "REFER_TO_HUMAN"
    assert result.recommendation.reason == "Auto-payment blocked due to invoice anomaly and high claim frequency"
    assert "Invoice date 2026-04-20 predates incident date 2026-04-25" in result.recommendation.risk_factors
    assert "Customer has 3 claims in the last 12 months" in result.recommendation.risk_factors

    task = task_service.get_task(result.human_task_id)
    assert task.task_type.value == "PAYMENT_REVIEW"
    assert task.created_reason == "Auto-payment blocked due to invoice anomaly and high claim frequency"
    assert task.recommended_payout_amount == 4200
    assert task.status.value == "OPEN"


def test_phase_2_modify_payout_resumes_and_creates_final_payment_instruction():
    claim_service = ClaimService()
    workflow_service = WorkflowService()
    task_service = HumanTaskService()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="CLM-2026-002",
            customer_id=999,
            policy_id=4,
            claim_type="motor",
            claim_amount=4200,
            incident_date="2026-04-25",
            description="Rear bumper damage after accident",
            documents=[
                DocumentUpload(
                    document_type=DocumentType.INVOICE,
                    file_name="repair-invoice.pdf",
                    storage_url="s3://claims/repair-invoice.pdf",
                    document_metadata={
                        "invoice_date": "2026-04-20",
                        "invoice_amount": 4200,
                        "vendor_name": "ABC Repairs",
                    },
                ),
                DocumentUpload(
                    document_type=DocumentType.PHOTO,
                    file_name="damage-photo.jpg",
                    storage_url="s3://claims/damage-photo.jpg",
                ),
                DocumentUpload(
                    document_type=DocumentType.REPAIR_ESTIMATE,
                    file_name="repair-estimate.pdf",
                    storage_url="s3://claims/repair-estimate.pdf",
                ),
            ],
        )
    )

    first_result = workflow_service.start_claim_workflow(created.claim.id)

    completed_task, resumed_result = workflow_service.complete_human_task(
        first_result.human_task_id,
        HumanTaskDecisionRequest(
            completed_by="adjuster_001",
            decision="MODIFY_PAYOUT",
            decision_notes="Approving only verified damage component. Reducing payout.",
            approved_amount=2800,
        ),
    )

    assert completed_task.reviewer_modified_payout_amount == 2800
    assert completed_task.completed_by == "adjuster_001"
    assert resumed_result.workflow_run.status == WorkflowRunStatus.COMPLETED
    assert resumed_result.payment_instruction_id is not None
    assert resumed_result.final_approved_amount == 2800
    assert resumed_result.final_decision == "APPROVE"
    assert resumed_result.claim_status == ClaimStatus.PAYMENT_READY.value
    assert claim_service.get_claim(created.claim.id).status == ClaimStatus.PAYMENT_READY
    detail = task_service.build_task_detail(
        task_service.get_task(first_result.human_task_id),
        claim_service.get_claim(created.claim.id),
        claim_service.get_claim_documents(created.claim.id),
    )
    assert detail.documents[0].document_metadata["invoice_date"] == "2026-04-20"
