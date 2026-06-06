from app.database import get_store
from app.agent.state import claims_review_graph
from app.agent.risk.risk_agent_graph import risk_agent_graph
from app.config import settings
from app.models.claim import ClaimStatus
from app.models.claim_document import DocumentType
from app.models.workflow_run import WorkflowRunStatus
from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema
from app.services.business_guardrails.guardrail_config import GuardrailConfig
from app.schemas.claim_schema import ClaimCreateRequest, DocumentUpload
from app.schemas.human_task_schema import HumanTaskDecisionRequest
from app.schemas.next_action_recommendation_schema import NextActionRecommendation
from app.services.case_packet import CasePacketBuilder
from app.services.claim_service import ClaimService
from app.services.human_task_service import HumanTaskService
from app.services.policy_admin_adapter import PolicyAdminAdapter
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
    claim = claim_service.get_claim(created.claim.id)
    assert claim.status == ClaimStatus.PAYMENT_READY
    assert claim.approved_reason == result.recommendation.reason
    assert claim.rejection_reason is None


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
    claim = claim_service.get_claim(created.claim.id)
    assert claim.status == ClaimStatus.PAYMENT_READY
    assert claim.approved_reason == "Approved after manual review"
    assert claim.rejection_reason is None


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
    assert task.adjuster_briefing is not None

    workflow_events = workflow_service.get_workflow_run_events(result.workflow_run.id)
    tool_events = [
        event for event in workflow_events if event.event_type.value == "ai_tool_executed"
    ]
    assert tool_events
    assert {event.event_payload["tool_name"] for event in tool_events} >= {
        "get_claim_history",
        "get_document_metadata",
    }


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


def test_adjuster_briefing_agent_output_is_stored_on_event_and_human_task():
    claim_service = ClaimService()
    original_threshold = GuardrailConfig.LARGE_CLAIM_AMOUNT_THRESHOLD
    GuardrailConfig.LARGE_CLAIM_AMOUNT_THRESHOLD = 10000
    try:
        workflow_service = WorkflowService()
        task_service = HumanTaskService()

        created = claim_service.submit_claim(
            ClaimCreateRequest(
                claim_number="AI-AGENT-001",
                customer_id=100,
                policy_id=1,
                claim_type="motor",
                claim_amount=9000,
                incident_date="2026-03-15",
                description="Clean file but high amount should require adjuster review at adjudication",
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

        assert result.workflow_run.status == WorkflowRunStatus.WAITING_FOR_HUMAN
        assert result.human_task_id is not None

        task = task_service.get_task(result.human_task_id)
        assert task.adjuster_briefing is not None
        assert "briefing_summary" in task.adjuster_briefing
        assert task.adjuster_briefing["why_workflow_paused"]

        workflow_events = workflow_service.get_workflow_run_events(result.workflow_run.id)
        evidence_events = [
            event for event in workflow_events if event.event_type.value == "ai_evidence_analysis_completed"
        ]
        risk_events = [
            event for event in workflow_events if event.event_type.value == "ai_risk_analysis_completed"
        ]
        ai_briefing_events = [
            event for event in workflow_events if event.event_type.value == "ai_adjuster_briefing_generated"
        ]
        briefing_events = [
            event for event in workflow_events if event.event_type.value == "adjuster_briefing_created"
        ]
        assert len(evidence_events) == 1
        assert evidence_events[0].event_payload["evidence_summary"]
        assert len(risk_events) == 1
        assert "risk_summary" in risk_events[0].event_payload
        assert len(ai_briefing_events) == 1
        assert ai_briefing_events[0].adjuster_briefing is not None
        assert len(briefing_events) == 1
        assert briefing_events[0].adjuster_briefing is not None
        assert briefing_events[0].adjuster_briefing["briefing_summary"] == task.adjuster_briefing["briefing_summary"]
        assert briefing_events[0].event_payload["evidence_analysis"] is not None
        assert briefing_events[0].event_payload["risk_analysis"] is not None
    finally:
        GuardrailConfig.LARGE_CLAIM_AMOUNT_THRESHOLD = original_threshold


def test_claims_review_graph_returns_evidence_risk_and_briefing():
    claim_service = ClaimService()
    policy_adapter = PolicyAdminAdapter()
    case_packet_builder = CasePacketBuilder()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="GRAPH-001",
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

    claim = claim_service.get_claim(created.claim.id)
    policy = policy_adapter.get_policy(claim.policy_id)
    case_packet = case_packet_builder.build(
        claim=claim,
        policy=policy,
        documents=claim_service.get_claim_documents(claim.id),
        coverage_result={"is_valid": True, "reasons": []},
        evidence_result={"is_valid": True, "reasons": [], "missing_documents": []},
        risk_result={"risk_score": 10, "risk_level": "LOW", "risk_factors": []},
        guardrail_results=[],
        recommendation={"recommendation": "APPROVE", "reason": "Claim passed automated checks"},
        claim_history_summary={"recent_30_day_claim_count": 0, "last_12_month_claim_count": 0},
        workflow_run_id=999,
    )

    graph_state = claims_review_graph.invoke({"case_packet": case_packet})

    assert graph_state["evidence_analysis"]["evidence_quality"] in {"good", "questionable"}
    assert "evidence_summary" in graph_state["evidence_analysis"]
    assert 0 <= graph_state["risk_analysis"]["risk_score"] <= 100
    assert graph_state["risk_analysis"]["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert "risk_summary" in graph_state["risk_analysis"]
    assert "briefing_summary" in graph_state["adjuster_briefing"]
    assert graph_state["adjuster_briefing"]["decision_options"]
    assert graph_state["recommended_next_action"]["next_action"] in {
        "PROCEED_TO_PAYMENT_GUARDRAILS",
        "CREATE_HUMAN_REVIEW_TASK",
        "REQUEST_MORE_INFO",
        "BLOCK_RECOMMENDED",
    }
    assert "reason" in graph_state["recommended_next_action"]


def test_claims_review_graph_recommends_human_review_for_high_risk_invoice_anomaly():
    claim_service = ClaimService()
    policy_adapter = PolicyAdminAdapter()
    case_packet_builder = CasePacketBuilder()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="GRAPH-ROUTE-001",
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

    claim = claim_service.get_claim(created.claim.id)
    policy = policy_adapter.get_policy(claim.policy_id)
    case_packet = case_packet_builder.build(
        claim=claim,
        policy=policy,
        documents=claim_service.get_claim_documents(claim.id),
        coverage_result={"is_valid": True, "reasons": []},
        evidence_result={"is_valid": True, "reasons": [], "missing_documents": []},
        risk_result={
            "risk_score": 72,
            "risk_level": "HIGH",
            "risk_factors": [
                "Invoice date predates incident date",
                "Customer has 3 prior claims in 12 months",
            ],
        },
        guardrail_results=[
            {
                "code": "INVOICE_DATE_BEFORE_INCIDENT",
                "decision": "REVIEW_REQUIRED",
                "message": "Invoice date predates incident date",
            },
            {
                "code": "REPEAT_CLAIMS_REVIEW_REQUIRED",
                "decision": "REVIEW_REQUIRED",
                "message": "Customer has 3 prior claims in 12 months",
            },
        ],
        recommendation={
            "recommendation": "REFER_TO_HUMAN",
            "reason": "High risk claim requires manual review",
        },
        claim_history_summary={"recent_30_day_claim_count": 0, "last_12_month_claim_count": 3},
        workflow_run_id=1000,
    )

    graph_state = claims_review_graph.invoke({"case_packet": case_packet})

    assert "get_claim_history" in graph_state["tool_results"]
    assert "get_document_metadata" in graph_state["tool_results"]
    assert set(graph_state["available_tools"]) == {
        "get_claim_history",
        "get_prior_rejection_details",
        "get_policy_coverage_summary",
        "get_document_metadata",
        "get_guardrail_results",
    }
    assert graph_state["recommended_next_action"]["next_action"] == "CREATE_HUMAN_REVIEW_TASK"
    assert graph_state["recommended_next_action"]["task_type"] == "PAYMENT_REVIEW"
    assert graph_state["recommended_next_action"]["priority"] == "HIGH"
    assert graph_state["recommended_next_action"]["requires_human_review"] is True


def test_risk_agent_graph_executes_read_tools_and_returns_structured_risk_analysis():
    claim_service = ClaimService()
    policy_adapter = PolicyAdminAdapter()
    case_packet_builder = CasePacketBuilder()

    created = claim_service.submit_claim(
        ClaimCreateRequest(
            claim_number="RISK-AGENT-001",
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

    claim = claim_service.get_claim(created.claim.id)
    policy = policy_adapter.get_policy(claim.policy_id)
    case_packet = case_packet_builder.build(
        claim=claim,
        policy=policy,
        documents=claim_service.get_claim_documents(claim.id),
        coverage_result={"is_valid": True, "reasons": []},
        evidence_result={"is_valid": True, "reasons": [], "missing_documents": []},
        risk_result={
            "risk_score": 30,
            "risk_level": "LOW",
            "risk_factors": ["Claim amount is greater than 80% of coverage limit"],
        },
        guardrail_results=[
            {
                "code": "INVOICE_DATE_BEFORE_INCIDENT",
                "decision": "REVIEW_REQUIRED",
                "severity": "HIGH",
                "message": "Invoice date 2026-04-20 predates incident date 2026-04-25",
            },
            {
                "code": "REPEAT_CLAIMS_REVIEW_REQUIRED",
                "decision": "REVIEW_REQUIRED",
                "severity": "HIGH",
                "message": "Customer has 3 claims in the last 12 months",
            },
        ],
        recommendation={"recommendation": "REFER_TO_HUMAN", "reason": "Manual review required"},
        claim_history_summary={"recent_30_day_claim_count": 0, "last_12_month_claim_count": 3},
        workflow_run_id=321,
    )

    result = risk_agent_graph.invoke(
        {
            "case_packet": case_packet,
            "tool_results": {},
            "previous_tool_calls": [],
            "selected_tool_decision": None,
            "latest_tool_result": None,
            "risk_analysis": None,
            "llm_calls": 0,
        }
    )

    assert result["risk_analysis"]["risk_level"] in {"MEDIUM", "HIGH"}
    assert result["previous_tool_calls"]
    assert {call["tool_name"] for call in result["previous_tool_calls"]} >= {
        "get_claim_history",
        "get_document_metadata",
    }


def test_agent_hitl_interrupt_pauses_after_agent_review(monkeypatch):
    claim_service = ClaimService()
    workflow_service = WorkflowService()
    original_flag = settings.agent_hitl_interrupt_enabled
    object.__setattr__(settings, "agent_hitl_interrupt_enabled", True)
    try:
        created = claim_service.submit_claim(
            ClaimCreateRequest(
                claim_number="HITL-001",
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

        fake_ai_review = {
            "graph_state": {},
            "evidence_analysis": None,
            "risk_analysis": None,
            "adjuster_briefing": AdjusterBriefingSchema(
                briefing_summary="AI summary",
                why_workflow_paused=["Manual confirmation required after AI review"],
                key_risk_factors=[],
                evidence_concerns=[],
                recommended_adjuster_actions=["Confirm payout"],
                questions_for_customer_or_repairer=[],
                decision_options=[],
                customer_safe_message="We are completing a final human review before payment.",
            ),
            "recommended_next_action": NextActionRecommendation(
                next_action="PROCEED_TO_PAYMENT_GUARDRAILS",
                reason="Proceed after human confirmation",
                task_type=None,
                priority="MEDIUM",
                requires_human_review=False,
                requires_more_information=False,
                blocking_reasons=[],
                supporting_factors=["AI review completed"],
            ),
        }

        monkeypatch.setattr(workflow_service, "_run_ai_claim_review", lambda *args, **kwargs: fake_ai_review)
        result = workflow_service.start_claim_workflow(created.claim.id)

        assert result.workflow_run.status == WorkflowRunStatus.WAITING_FOR_HUMAN
        assert result.human_task_id is not None
        task = HumanTaskService().get_task(result.human_task_id)
        assert task.task_type.value == "AGENT_REVIEW"
        events = workflow_service.get_workflow_run_events(result.workflow_run.id)
        assert any(event.event_type.value == "ai_hitl_interrupt_created" for event in events)
    finally:
        object.__setattr__(settings, "agent_hitl_interrupt_enabled", original_flag)
