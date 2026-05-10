from decimal import Decimal

from app.database import get_store
from app.models.claim_document import DocumentType
from app.schemas.claim_schema import ClaimCreateRequest, DocumentUpload
from app.services.business_guardrails import BusinessGuardrailService, GuardrailDecision
from app.services.claim_service import ClaimService


def setup_function():
    get_store().reset()


def test_pre_adjudication_review_required_for_suspicious_claim():
    claim_service = ClaimService()
    guardrail_service = BusinessGuardrailService(claim_service=claim_service)

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="GR-001",
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
                    document_metadata={"invoice_date": "2026-04-20", "invoice_amount": 4200},
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

    summary = guardrail_service.evaluate_pre_adjudication(created.claim.id)

    assert summary.overall_decision == GuardrailDecision.REVIEW_REQUIRED
    assert any(result.code == "INVOICE_DATE_BEFORE_INCIDENT" for result in summary.review_results)
    assert any(result.code == "REPEAT_CLAIMS_REVIEW_REQUIRED" for result in summary.review_results)


def test_pre_adjudication_block_for_inactive_policy():
    claim_service = ClaimService()
    guardrail_service = BusinessGuardrailService(claim_service=claim_service)

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="GR-002",
            customer_id=102,
            policy_id=3,
            claim_type="motor",
            claim_amount=1200,
            incident_date="2025-06-15",
            description="Claim against expired policy",
            documents=[],
        )
    )

    summary = guardrail_service.evaluate_pre_adjudication(created.claim.id)

    assert summary.overall_decision == GuardrailDecision.BLOCK
    assert any(result.code == "POLICY_NOT_ACTIVE" for result in summary.blocking_results)


def test_pre_payment_blocks_high_risk_without_human_approval():
    claim_service = ClaimService()
    guardrail_service = BusinessGuardrailService(claim_service=claim_service)

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="GR-003",
            customer_id=100,
            policy_id=1,
            claim_type="motor",
            claim_amount=4200,
            incident_date="2026-03-05",
            description="Standard claim for payment guardrail test",
            documents=[],
        )
    )

    summary = guardrail_service.evaluate_pre_payment(
        claim_id=created.claim.id,
        approved_amount=Decimal("4200"),
        final_payout_amount=Decimal("4200"),
        human_approval_present=False,
        is_high_risk=True,
    )

    assert summary.overall_decision == GuardrailDecision.BLOCK
    assert any(result.code == "HIGH_RISK_PAYMENT_REQUIRES_HUMAN_APPROVAL" for result in summary.blocking_results)
