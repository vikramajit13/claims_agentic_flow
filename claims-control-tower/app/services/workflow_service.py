from __future__ import annotations

from app.enums import RecommendationDecision
from app.models.claim import ClaimStatus
from app.models.workflow_event import ActorType, WorkflowEventType
from app.models.workflow_run import WorkflowRunStep
from app.repositories.claim_repository import ClaimRepository
from app.repositories.human_task_repository import HumanTaskRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.schemas.human_task_schema import HumanTaskDecisionRequest
from app.schemas.payment_schema import PaymentInstructionResponse
from app.schemas.workflow_schema import (
    AdjudicationRecommendation,
    WorkflowExecutionResponse,
    WorkflowRunDetail,
)
from app.services.adjudication_service import AdjudicationService
from app.services.audit_service import AuditService
from app.services.claim_service import ClaimService
from app.services.claims_system_adapter import ClaimsSystemAdapter
from app.services.document_validation_service import DocumentValidationService
from app.services.fraud_risk_service import FraudRiskService
from app.services.human_task_service import HumanTaskService
from app.services.payment_adapter import PaymentAdapter
from app.services.payment_guardrail_service import PaymentGuardrailService
from app.services.policy_admin_adapter import PolicyAdminAdapter


class WorkflowService:
    def __init__(self) -> None:
        self.claim_repo = ClaimRepository()
        self.workflow_repo = WorkflowRepository()
        self.human_task_repo = HumanTaskRepository()
        self.payment_repo = PaymentRepository()
        self.claim_service = ClaimService(self.claim_repo)
        self.claims_system = ClaimsSystemAdapter(self.claim_repo)
        self.policy_adapter = PolicyAdminAdapter()
        self.document_service = DocumentValidationService()
        self.fraud_service = FraudRiskService()
        self.adjudication_service = AdjudicationService()
        self.human_task_service = HumanTaskService(self.human_task_repo)
        self.payment_guardrail_service = PaymentGuardrailService()
        self.payment_adapter = PaymentAdapter(self.payment_repo)
        self.audit = AuditService()

    def start_claim_workflow(self, claim_id: int) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.create(claim_id)
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.WORKFLOW_STARTED,
            WorkflowRunStep.CLAIM_INTAKE.value,
            {"message": "Workflow run created"},
        )
        return self.execute(workflow_run.id)

    def execute(self, workflow_run_id: int) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.get(workflow_run_id)
        claim = self.claim_repo.get(workflow_run.claim_id)
        self.claims_system.update_claim_status(claim.id, ClaimStatus.IN_REVIEW)

        try:
            workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.COVERAGE_VALIDATION)
            self.audit.record_step_started(workflow_run, WorkflowRunStep.COVERAGE_VALIDATION.value)
            coverage_result = self.policy_adapter.validate_coverage(claim)
            self.audit.record_step_completed(
                workflow_run,
                WorkflowRunStep.COVERAGE_VALIDATION.value,
                coverage_result.dict(),
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.POLICY_VALIDATED,
                WorkflowRunStep.COVERAGE_VALIDATION.value,
                coverage_result.dict(),
            )

            if not coverage_result.is_valid:
                recommendation = self.adjudication_service.reject(claim, coverage_result.reasons)
                self.claims_system.update_claim_status(claim.id, ClaimStatus.REJECTED)
                workflow_run = self.workflow_repo.complete(workflow_run.id)
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.RECOMMENDATION_CREATED,
                    WorkflowRunStep.ADJUDICATION.value,
                    recommendation.dict(),
                )
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.WORKFLOW_COMPLETED,
                    WorkflowRunStep.COMPLETED.value,
                    {"outcome": "rejected"},
                )
                return WorkflowExecutionResponse(workflow_run=workflow_run, recommendation=recommendation)

            workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.EVIDENCE_VALIDATION)
            self.audit.record_step_started(workflow_run, WorkflowRunStep.EVIDENCE_VALIDATION.value)
            evidence_result = self.document_service.validate_documents(claim)
            self.audit.record_step_completed(
                workflow_run,
                WorkflowRunStep.EVIDENCE_VALIDATION.value,
                evidence_result.dict(),
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.DOCUMENTS_VALIDATED,
                WorkflowRunStep.EVIDENCE_VALIDATION.value,
                evidence_result.dict(),
            )

            workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.FRAUD_RISK_CHECK)
            self.audit.record_step_started(workflow_run, WorkflowRunStep.FRAUD_RISK_CHECK.value)
            policy = self.policy_adapter.get_policy(claim.policy_id)
            recent_claims = self.claim_repo.get_recent_customer_claims(claim.customer_id, 30, exclude_claim_id=claim.id)
            risk_result = self.fraud_service.evaluate(claim, policy, evidence_result, len(recent_claims))
            self.audit.record_step_completed(
                workflow_run,
                WorkflowRunStep.FRAUD_RISK_CHECK.value,
                risk_result.dict(),
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.FRAUD_RULES_EVALUATED,
                WorkflowRunStep.FRAUD_RISK_CHECK.value,
                risk_result.dict(),
            )

            workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.ADJUDICATION)
            recommendation = self.adjudication_service.recommend(
                claim=claim,
                coverage_result=coverage_result,
                evidence_result=evidence_result,
                risk_result=risk_result,
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.RECOMMENDATION_CREATED,
                WorkflowRunStep.ADJUDICATION.value,
                recommendation.dict(),
            )

            if recommendation.recommendation == RecommendationDecision.REQUEST_MORE_INFO:
                self.claims_system.update_claim_status(claim.id, ClaimStatus.PENDING_MORE_INFO)
                workflow_run = self.workflow_repo.mark_waiting_for_info(workflow_run.id)
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.WORKFLOW_WAITING_FOR_INFO,
                    WorkflowRunStep.ADJUDICATION.value,
                    recommendation.dict(),
                )
                return WorkflowExecutionResponse(workflow_run=workflow_run, recommendation=recommendation)

            if recommendation.requires_human_review:
                workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.HUMAN_REVIEW)
                task = self.human_task_service.create_task(claim.id, workflow_run.id, recommendation)
                workflow_run = self.workflow_repo.mark_waiting_for_human(workflow_run.id)
                self.claims_system.update_claim_status(claim.id, ClaimStatus.PENDING_HUMAN_REVIEW)
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.HUMAN_TASK_CREATED,
                    WorkflowRunStep.HUMAN_REVIEW.value,
                    task.dict(),
                )
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.WORKFLOW_WAITING_FOR_HUMAN,
                    WorkflowRunStep.HUMAN_REVIEW.value,
                    {"human_task_id": task.id},
                )
                return WorkflowExecutionResponse(
                    workflow_run=workflow_run,
                    recommendation=recommendation,
                    human_task_id=task.id,
                )

            self.claims_system.update_claim_status(claim.id, ClaimStatus.APPROVED)
            return self._continue_to_payment(workflow_run.id, recommendation, has_human_approval=False)

        except KeyError as exc:
            workflow_run = self.workflow_repo.fail(workflow_run.id, str(exc))
            self.audit.record_step_failed(workflow_run, workflow_run.current_step.value, str(exc))
            raise
        except Exception as exc:  # pragma: no cover
            workflow_run = self.workflow_repo.fail(workflow_run.id, str(exc))
            self.audit.record_step_failed(workflow_run, workflow_run.current_step.value, str(exc))
            raise

    def pause_workflow(self, workflow_run_id: int, reason: str | None = None) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.pause(workflow_run_id, reason)
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.WORKFLOW_PAUSED,
            workflow_run.current_step.value,
            {"reason": reason},
        )
        return WorkflowExecutionResponse(workflow_run=workflow_run)

    def resume_workflow(self, workflow_run_id: int) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.resume(workflow_run_id)
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.WORKFLOW_RESUMED,
            workflow_run.current_step.value,
            {"message": "Workflow resumed"},
        )
        return self.execute(workflow_run.id)

    def complete_human_task(self, task_id: int, request: HumanTaskDecisionRequest):
        task = self.human_task_service.complete_task(task_id, request.decision, request.decision_notes)
        workflow_run = self.workflow_repo.resume(task.workflow_run_id)
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.HUMAN_TASK_COMPLETED,
            WorkflowRunStep.HUMAN_REVIEW.value,
            task.dict(),
            actor_type=ActorType.HUMAN_REVIEWER,
            actor_id=request.reviewer_id,
        )
        result = self.resume_from_human_decision(task.id, request)
        return task, result

    def resume_from_human_decision(
        self,
        task_id: int,
        request: HumanTaskDecisionRequest,
    ) -> WorkflowExecutionResponse:
        task = self.human_task_repo.get(task_id)
        workflow_run = self.workflow_repo.resume(task.workflow_run_id)
        claim = self.claim_repo.get(task.claim_id)

        if request.decision.upper() == RecommendationDecision.REJECT.value:
            self.claims_system.update_claim_status(claim.id, ClaimStatus.REJECTED)
            workflow_run = self.workflow_repo.complete(workflow_run.id)
            recommendation = AdjudicationRecommendation(
                recommendation=RecommendationDecision.REJECT,
                reason=request.decision_notes or "Rejected by human reviewer",
                recommended_amount=0.0,
                requires_human_review=False,
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.WORKFLOW_COMPLETED,
                WorkflowRunStep.COMPLETED.value,
                {"outcome": "rejected_after_human_review"},
            )
            return WorkflowExecutionResponse(workflow_run=workflow_run, recommendation=recommendation)

        if request.decision.upper() == RecommendationDecision.REQUEST_MORE_INFO.value:
            self.claims_system.update_claim_status(claim.id, ClaimStatus.PENDING_MORE_INFO)
            workflow_run = self.workflow_repo.mark_waiting_for_info(workflow_run.id)
            recommendation = AdjudicationRecommendation(
                recommendation=RecommendationDecision.REQUEST_MORE_INFO,
                reason=request.decision_notes or "Human reviewer requested more information",
                recommended_amount=0.0,
                requires_human_review=False,
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.WORKFLOW_WAITING_FOR_INFO,
                WorkflowRunStep.HUMAN_REVIEW.value,
                recommendation.dict(),
            )
            return WorkflowExecutionResponse(workflow_run=workflow_run, recommendation=recommendation)

        recommendation = AdjudicationRecommendation(
            recommendation=RecommendationDecision.APPROVE,
            reason=request.decision_notes or "Approved by human reviewer",
            recommended_amount=claim.claim_amount,
            requires_human_review=False,
        )
        self.claims_system.update_claim_status(claim.id, ClaimStatus.APPROVED)
        return self._continue_to_payment(workflow_run.id, recommendation, has_human_approval=True)

    def _continue_to_payment(
        self,
        workflow_run_id: int,
        recommendation: AdjudicationRecommendation,
        has_human_approval: bool,
    ) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.get(workflow_run_id)
        claim = self.claim_repo.get(workflow_run.claim_id)
        policy = self.policy_adapter.get_policy(claim.policy_id)

        workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.PAYMENT_GUARDRAIL)
        self.audit.record_step_started(workflow_run, WorkflowRunStep.PAYMENT_GUARDRAIL.value)
        guardrail_result = self.payment_guardrail_service.validate(
            claim,
            policy,
            recommendation,
            has_human_approval=has_human_approval,
        )
        self.audit.record_step_completed(
            workflow_run,
            WorkflowRunStep.PAYMENT_GUARDRAIL.value,
            guardrail_result.dict(),
        )

        if not guardrail_result.passed:
            self.claims_system.update_claim_status(claim.id, ClaimStatus.PAYMENT_BLOCKED)
            workflow_run = self.workflow_repo.complete(workflow_run.id)
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.PAYMENT_GUARDRAIL_FAILED,
                WorkflowRunStep.PAYMENT_GUARDRAIL.value,
                guardrail_result.dict(),
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.WORKFLOW_COMPLETED,
                WorkflowRunStep.COMPLETED.value,
                {"outcome": "payment_blocked"},
            )
            return WorkflowExecutionResponse(workflow_run=workflow_run, recommendation=recommendation)

        self.audit.record_event(
            workflow_run,
            WorkflowEventType.PAYMENT_GUARDRAIL_PASSED,
            WorkflowRunStep.PAYMENT_GUARDRAIL.value,
            guardrail_result.dict(),
        )

        workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.PAYMENT_INSTRUCTION)
        self.audit.record_step_started(workflow_run, WorkflowRunStep.PAYMENT_INSTRUCTION.value)
        payment_instruction = self.payment_adapter.create_payment_instruction(
            claim_id=claim.id,
            workflow_run_id=workflow_run.id,
            amount=recommendation.recommended_amount,
            customer_id=claim.customer_id,
        )
        self.claims_system.update_claim_status(claim.id, ClaimStatus.PAYMENT_READY)
        workflow_run = self.workflow_repo.complete(workflow_run.id)
        self.audit.record_step_completed(
            workflow_run,
            WorkflowRunStep.PAYMENT_INSTRUCTION.value,
            payment_instruction.dict(),
        )
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.PAYMENT_INSTRUCTION_CREATED,
            WorkflowRunStep.PAYMENT_INSTRUCTION.value,
            payment_instruction.dict(),
            actor_type=ActorType.PAYMENT_SERVICE,
            actor_id="mock_payment_adapter",
        )
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.WORKFLOW_COMPLETED,
            WorkflowRunStep.COMPLETED.value,
            {"outcome": "payment_ready"},
        )
        return WorkflowExecutionResponse(
            workflow_run=workflow_run,
            recommendation=recommendation,
            payment_instruction_id=payment_instruction.id,
        )

    def get_workflow_run(self, workflow_run_id: int) -> WorkflowRunDetail:
        workflow_run = self.workflow_repo.get(workflow_run_id)
        events = self.audit.get_workflow_events(workflow_run_id)
        return WorkflowRunDetail(workflow_run=workflow_run, events=events)

    def get_all_workflows(self):
        return self.workflow_repo.list()

    def get_workflow_run_events(self, workflow_run_id: int):
        return self.audit.get_workflow_events(workflow_run_id)

    def get_claim_audit(self, claim_id: int):
        return self.audit.get_claim_audit(claim_id)

    def get_all_payment_instructions(self):
        return self.payment_repo.list()

    def get_payment_instruction(self, payment_instruction_id: int) -> PaymentInstructionResponse:
        return PaymentInstructionResponse(payment_instruction=self.payment_repo.get(payment_instruction_id))
