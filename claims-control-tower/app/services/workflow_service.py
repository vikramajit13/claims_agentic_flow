from __future__ import annotations

from decimal import Decimal
from app.services.observability import run_claims_review_graph, traceable
from app.enums import HumanDecision, RecommendationDecision
from app.models.claim import ClaimStatus
from app.models.human_task import HumanTaskPriority, HumanTaskType
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
from app.services.business_guardrails import (
    BusinessGuardrailService,
    GuardrailCategory,
    GuardrailDecision,
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
from app.services.risk_signal_service import RiskSignalService
from app.services.case_packet import CasePacketBuilder
from app.services.adjuster_briefing_service import AdjusterBriefingAgent
from app.agent.state import claims_review_graph
from app.schemas.evidence_analysis_schema import EvidenceAnalysisSchema
from app.schemas.investigation_schema import InformationGap, ToolExecutionRecord
from app.schemas.Adjuster_briefing_schema import AdjusterBriefingSchema
from app.schemas.next_action_recommendation_schema import NextActionRecommendation
from app.schemas.risk_analysis_schema import RiskAnalysisSchema


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
        self.business_guardrails = BusinessGuardrailService(
            claim_repository=self.claim_repo,
            policy_repository=self.policy_adapter.policy_repo,
            claim_service=self.claim_service,
        )
        self.fraud_service = FraudRiskService()
        self.adjudication_service = AdjudicationService()
        self.human_task_service = HumanTaskService(self.human_task_repo)
        self.payment_guardrail_service = PaymentGuardrailService()
        self.payment_adapter = PaymentAdapter(self.payment_repo)
        self.risk_signal_service = RiskSignalService()
        self.audit = AuditService()
        self.case_packet_builder = CasePacketBuilder()
        self.adjuster_briefing_agent = AdjusterBriefingAgent()

    def start_claim_workflow(self, claim_id: int) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.create(claim_id)
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.WORKFLOW_STARTED,
            WorkflowRunStep.CLAIM_INTAKE.value,
            {"message": "Workflow run created"},
        )
        return self.execute(workflow_run.id)
    
    @traceable(name="workflow_execute", run_type="chain")
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
                self.claims_system.update_claim_status(
                    claim.id,
                    ClaimStatus.REJECTED,
                    rejection_reason=recommendation.reason,
                    approved_reason=None,
                )
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

            pre_adjudication_summary = self.business_guardrails.evaluate_pre_adjudication(claim.id)
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.BUSINESS_GUARDRAILS_EVALUATED,
                "PRE_ADJUDICATION_GUARDRAILS",
                {
                    "overall_decision": pre_adjudication_summary.overall_decision.value,
                    "results": [result.dict() for result in pre_adjudication_summary.results],
                },
            )

            if pre_adjudication_summary.overall_decision == GuardrailDecision.BLOCK:
                reasons = [result.message for result in pre_adjudication_summary.blocking_results]
                recommendation = self.adjudication_service.reject(claim, reasons)
                self.claims_system.update_claim_status(
                    claim.id,
                    ClaimStatus.REJECTED,
                    rejection_reason=recommendation.reason,
                    approved_reason=None,
                )
                workflow_run = self.workflow_repo.complete(workflow_run.id)
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.WORKFLOW_COMPLETED,
                    WorkflowRunStep.COMPLETED.value,
                    {"outcome": "guardrail_blocked", "reasons": reasons},
                )
                return WorkflowExecutionResponse(
                    workflow_run=workflow_run,
                    recommendation=recommendation,
                    claim_status=ClaimStatus.REJECTED.value,
                    final_decision=RecommendationDecision.REJECT.value,
                    final_approved_amount=0.0,
                )

            if pre_adjudication_summary.overall_decision == GuardrailDecision.REVIEW_REQUIRED:
                review_results = pre_adjudication_summary.review_results
                reason = self._guardrail_review_reason(review_results)
                recommendation = AdjudicationRecommendation(
                    recommendation=RecommendationDecision.REFER_TO_HUMAN,
                    reason=reason,
                    recommended_amount=claim.claim_amount,
                    requires_human_review=True,
                    risk_factors=[result.message for result in review_results],
                    recommended_action="BUSINESS_GUARDRAIL_REVIEW_REQUIRED",
                )
                guardrail_results = [result.dict() for result in pre_adjudication_summary.results]
                claim_history_summary = {
                    "recent_30_day_claim_count": len(recent_claims),
                    "last_12_month_claim_count": len(
                        self.claims_system.get_claims_for_customer_last_12_months(
                            claim.customer_id,
                            claim.incident_date,
                            exclude_claim_id=claim.id,
                        )
                    ),
                }
                case_packet = self.case_packet_builder.build(
                    claim=claim,
                    policy=policy,
                    documents=self.claim_service.get_claim_documents(claim.id),
                    coverage_result=coverage_result.dict(),
                    evidence_result=evidence_result.dict(),
                    risk_result=risk_result.dict(),
                    guardrail_results=guardrail_results,
                    recommendation=recommendation.dict(),
                    claim_history_summary=claim_history_summary,
                    workflow_run_id=workflow_run.id,
                )
                ai_review = self._run_ai_claim_review(
                    workflow_run=workflow_run,
                    case_packet=case_packet,
                    step_name=WorkflowRunStep.HUMAN_REVIEW.value,
                )
                task_type = self._task_type_for_guardrail_results(review_results)
                return self._pause_for_human_review(
                    workflow_run=workflow_run,
                    claim_id=claim.id,
                    task_type=task_type,
                    reason=recommendation.reason,
                    risk_factors=recommendation.risk_factors,
                    recommendation=recommendation,
                    adjuster_briefing=(
                        ai_review["adjuster_briefing"].dict() if ai_review["adjuster_briefing"] else None
                    ),
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
            
       
            

            guardrail_results = [result.dict() for result in pre_adjudication_summary.results]
            claim_history_summary = {
                "recent_30_day_claim_count": len(recent_claims),
                "last_12_month_claim_count": len(
                    self.claims_system.get_claims_for_customer_last_12_months(
                        claim.customer_id,
                        claim.incident_date,
                        exclude_claim_id=claim.id,
                    )
                ),
            }
            case_packet = self.case_packet_builder.build(
                claim=claim,
                policy=policy,
                documents=self.claim_service.get_claim_documents(claim.id),
                coverage_result=coverage_result.dict(),
                evidence_result=evidence_result.dict(),
                risk_result=risk_result.dict(),
                guardrail_results=guardrail_results,
                recommendation=recommendation.dict(),
                claim_history_summary=claim_history_summary,
                workflow_run_id=workflow_run.id,
            )

            ai_review = self._run_ai_claim_review(
                workflow_run=workflow_run,
                case_packet=case_packet,
                step_name=WorkflowRunStep.ADJUDICATION.value,
            )
            evidence_analysis = ai_review["evidence_analysis"]
            risk_analysis = ai_review["risk_analysis"]
            adjuster_briefing = ai_review["adjuster_briefing"]
            recommended_next_action = ai_review["recommended_next_action"]

            if recommendation.requires_human_review and adjuster_briefing is not None:
                self.audit.record_event(
                    workflow_run,
                    WorkflowEventType.ADJUSTER_BRIEFING_CREATED,
                    WorkflowRunStep.ADJUDICATION.value,
                    {
                        "case_packet": case_packet.dict(),
                        "evidence_analysis": evidence_analysis.dict() if evidence_analysis else None,
                        "risk_analysis": risk_analysis.dict() if risk_analysis else None,
                        "recommended_next_action": (
                            recommended_next_action.dict() if recommended_next_action else None
                        ),
                    },
                    adjuster_briefing=adjuster_briefing.dict(),
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
                task_type = HumanTaskType.FRAUD_REVIEW
                if recommendation.recommended_action == "PAYMENT_REVIEW_REQUIRED":
                    task_type = HumanTaskType.PAYMENT_REVIEW
                return self._pause_for_human_review(
                    workflow_run=workflow_run,
                    claim_id=claim.id,
                    task_type=task_type,
                    reason=recommendation.reason,
                    risk_factors=recommendation.risk_factors,
                    recommendation=recommendation,
                    adjuster_briefing=adjuster_briefing.dict() if adjuster_briefing else None,
                )

            self.claims_system.update_claim_status(
                claim.id,
                ClaimStatus.APPROVED,
                rejection_reason=None,
                approved_reason=recommendation.reason,
            )
            is_high_risk = risk_result.risk_level.value == "HIGH"
            return self._continue_to_payment(
                workflow_run.id,
                recommendation,
                has_human_approval=False,
                is_high_risk=is_high_risk,
            )

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
        task = self.human_task_service.complete_task(
            task_id,
            request.decision,
            request.decision_notes,
            request.completed_by,
            request.approved_amount,
        )
        workflow_run = self.workflow_repo.resume(task.workflow_run_id)
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.HUMAN_TASK_COMPLETED,
            WorkflowRunStep.HUMAN_REVIEW.value,
            task.dict(),
            actor_type=ActorType.HUMAN_REVIEWER,
            actor_id=request.completed_by,
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

        if request.decision == HumanDecision.REJECT:
            self.claims_system.update_claim_status(
                claim.id,
                ClaimStatus.REJECTED,
                rejection_reason=request.decision_notes or "Rejected by human reviewer",
                approved_reason=None,
            )
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
            return WorkflowExecutionResponse(
                workflow_run=workflow_run,
                recommendation=recommendation,
                claim_status=ClaimStatus.REJECTED.value,
                final_decision=RecommendationDecision.REJECT.value,
                final_approved_amount=0.0,
            )

        if request.decision == HumanDecision.REQUEST_MORE_INFO:
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
            return WorkflowExecutionResponse(
                workflow_run=workflow_run,
                recommendation=recommendation,
                claim_status=ClaimStatus.PENDING_MORE_INFO.value,
                final_decision=RecommendationDecision.REQUEST_MORE_INFO.value,
            )

        if request.decision == HumanDecision.ESCALATE:
            recommendation = AdjudicationRecommendation(
                recommendation=RecommendationDecision.REFER_TO_HUMAN,
                reason=request.decision_notes or "Escalated for additional human review",
                recommended_amount=request.approved_amount or task.recommended_payout_amount or claim.claim_amount,
                requires_human_review=True,
                risk_factors=task.risk_factors,
                recommended_action="ADDITIONAL_REVIEW_REQUIRED",
            )
            return self._pause_for_human_review(
                workflow_run=workflow_run,
                claim_id=claim.id,
                task_type=HumanTaskType.CLAIM_REVIEW,
                reason=recommendation.reason,
                risk_factors=recommendation.risk_factors,
                recommendation=recommendation,
            )

        approved_amount = request.approved_amount or task.recommended_payout_amount or claim.claim_amount
        if request.decision == HumanDecision.MODIFY_PAYOUT and request.approved_amount is None:
            raise ValueError("approved_amount is required when decision is MODIFY_PAYOUT")

        recommendation = AdjudicationRecommendation(
            recommendation=RecommendationDecision.APPROVE,
            reason=request.decision_notes or "Approved by human reviewer",
            recommended_amount=approved_amount,
            requires_human_review=False,
            risk_factors=task.risk_factors,
            recommended_action="HUMAN_APPROVED",
        )
        self.claims_system.update_claim_status(
            claim.id,
            ClaimStatus.APPROVED,
            rejection_reason=None,
            approved_reason=recommendation.reason,
        )
        is_high_risk = task.task_type in {HumanTaskType.FRAUD_REVIEW, HumanTaskType.PAYMENT_REVIEW}
        return self._continue_to_payment(
            workflow_run.id,
            recommendation,
            has_human_approval=True,
            is_high_risk=is_high_risk,
        )

    def _continue_to_payment(
        self,
        workflow_run_id: int,
        recommendation: AdjudicationRecommendation,
        has_human_approval: bool,
        is_high_risk: bool,
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
        pre_payment_summary = self.business_guardrails.evaluate_pre_payment(
            claim_id=claim.id,
            approved_amount=Decimal(str(recommendation.recommended_amount)),
            final_payout_amount=Decimal(str(recommendation.recommended_amount)),
            human_approval_present=has_human_approval,
            is_high_risk=is_high_risk,
        )
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.BUSINESS_GUARDRAILS_EVALUATED,
            "PRE_PAYMENT_GUARDRAILS",
            {
                "overall_decision": pre_payment_summary.overall_decision.value,
                "results": [result.dict() for result in pre_payment_summary.results],
            },
        )
        self.audit.record_step_completed(
            workflow_run,
            WorkflowRunStep.PAYMENT_GUARDRAIL.value,
            {
                "payment_guardrails": guardrail_result.dict(),
                "business_guardrails": pre_payment_summary.dict(),
            },
        )

        block_results = pre_payment_summary.blocking_results
        review_results = pre_payment_summary.review_results
        if (
            not guardrail_result.passed
            or block_results
            or (review_results and not has_human_approval)
        ):
            reasons = list(guardrail_result.reasons)
            reasons.extend(result.message for result in block_results + review_results)

            if review_results and not has_human_approval:
                recommendation = AdjudicationRecommendation(
                    recommendation=RecommendationDecision.REFER_TO_HUMAN,
                    reason="Payment review required",
                    recommended_amount=recommendation.recommended_amount,
                    requires_human_review=True,
                    risk_factors=reasons,
                    recommended_action="PAYMENT_REVIEW_REQUIRED",
                )
                return self._pause_for_human_review(
                    workflow_run=workflow_run,
                    claim_id=claim.id,
                    task_type=HumanTaskType.PAYMENT_REVIEW,
                    reason="Payment review required",
                    risk_factors=reasons,
                    recommendation=recommendation,
                )

            if not has_human_approval:
                recommendation = AdjudicationRecommendation(
                    recommendation=RecommendationDecision.REFER_TO_HUMAN,
                    reason="Payment review required",
                    recommended_amount=recommendation.recommended_amount,
                    requires_human_review=True,
                    risk_factors=reasons,
                    recommended_action="PAYMENT_REVIEW_REQUIRED",
                )
                return self._pause_for_human_review(
                    workflow_run=workflow_run,
                    claim_id=claim.id,
                    task_type=HumanTaskType.PAYMENT_REVIEW,
                    reason="Payment review required",
                    risk_factors=reasons,
                    recommendation=recommendation,
                )
            self.claims_system.update_claim_status(
                claim.id,
                ClaimStatus.PAYMENT_BLOCKED,
                approved_reason=claim.approved_reason or recommendation.reason,
            )
            workflow_run = self.workflow_repo.complete(workflow_run.id)
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.PAYMENT_GUARDRAIL_FAILED,
                WorkflowRunStep.PAYMENT_GUARDRAIL.value,
                {"reasons": reasons},
            )
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.WORKFLOW_COMPLETED,
                WorkflowRunStep.COMPLETED.value,
                {"outcome": "payment_blocked"},
            )
            return WorkflowExecutionResponse(
                workflow_run=workflow_run,
                recommendation=recommendation,
                claim_status=ClaimStatus.PAYMENT_BLOCKED.value,
                final_decision=RecommendationDecision.APPROVE.value,
                final_approved_amount=recommendation.recommended_amount,
            )

            self.audit.record_event(
                workflow_run,
                WorkflowEventType.PAYMENT_GUARDRAIL_PASSED,
                WorkflowRunStep.PAYMENT_GUARDRAIL.value,
                {
                    "payment_guardrails": guardrail_result.dict(),
                    "business_guardrails": pre_payment_summary.dict(),
                },
            )

        workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.PAYMENT_INSTRUCTION)
        self.audit.record_step_started(workflow_run, WorkflowRunStep.PAYMENT_INSTRUCTION.value)
        payment_instruction = self.payment_adapter.create_payment_instruction(
            claim_id=claim.id,
            workflow_run_id=workflow_run.id,
            amount=recommendation.recommended_amount,
            customer_id=claim.customer_id,
        )
        self.claims_system.update_claim_status(
            claim.id,
            ClaimStatus.PAYMENT_READY,
            approved_reason=claim.approved_reason or recommendation.reason,
        )
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
            claim_status=ClaimStatus.PAYMENT_READY.value,
            final_decision=RecommendationDecision.APPROVE.value,
            final_approved_amount=recommendation.recommended_amount,
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

    def _task_type_for_guardrail_results(self, results) -> HumanTaskType:
        codes = {result.code for result in results}
        if {"INVOICE_DATE_BEFORE_INCIDENT", "REPEAT_CLAIMS_REVIEW_REQUIRED"}.issubset(codes):
            return HumanTaskType.PAYMENT_REVIEW
        if any(result.category == GuardrailCategory.PAYMENT for result in results):
            return HumanTaskType.PAYMENT_REVIEW
        if any(result.category == GuardrailCategory.FRAUD_RISK for result in results):
            return HumanTaskType.FRAUD_REVIEW
        return HumanTaskType.CLAIM_REVIEW

    def _guardrail_review_reason(self, results) -> str:
        codes = {result.code for result in results}
        if {"INVOICE_DATE_BEFORE_INCIDENT", "REPEAT_CLAIMS_REVIEW_REQUIRED"}.issubset(codes):
            return "Auto-payment blocked due to invoice anomaly and high claim frequency"
        return "; ".join(result.message for result in results)

    def _pause_for_human_review(
        self,
        workflow_run,
        claim_id: int,
        task_type: HumanTaskType,
        reason: str,
        risk_factors: list[str],
        recommendation: AdjudicationRecommendation,
        adjuster_briefing: dict | None = None,
    ) -> WorkflowExecutionResponse:
        workflow_run = self.workflow_repo.update_step(workflow_run.id, WorkflowRunStep.HUMAN_REVIEW)
        workflow_run = self.workflow_repo.mark_waiting_for_human(workflow_run.id)
        self.claims_system.update_claim_status(claim_id, ClaimStatus.PENDING_HUMAN_REVIEW)
        task = self.human_task_service.create_task(
            claim_id=claim_id,
            workflow_run_id=workflow_run.id,
            recommendation=recommendation,
            task_type=task_type,
            priority=HumanTaskPriority.HIGH,
            assigned_to=None,
            created_reason=reason,
            risk_factors=risk_factors,
            adjuster_briefing=adjuster_briefing,
        )
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.HUMAN_TASK_CREATED,
            WorkflowRunStep.HUMAN_REVIEW.value,
            task.dict(),
            adjuster_briefing=adjuster_briefing,
        )
        self.audit.record_event(
            workflow_run,
            WorkflowEventType.WORKFLOW_PAUSED,
            WorkflowRunStep.HUMAN_REVIEW.value,
            {"reason": reason, "task_id": task.id, "risk_factors": risk_factors},
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
            claim_status=ClaimStatus.PENDING_HUMAN_REVIEW.value,
            final_decision=recommendation.recommendation.value,
            final_approved_amount=recommendation.recommended_amount,
        )

    def _run_ai_claim_review(self, workflow_run, case_packet, step_name: str):
        graph_state = run_claims_review_graph(claims_review_graph, case_packet)
        evidence_analysis = None
        risk_analysis = None
        adjuster_briefing = None
        recommended_next_action = None

        if graph_state.get("evidence_analysis"):
            evidence_analysis = EvidenceAnalysisSchema(**graph_state["evidence_analysis"])
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.AI_EVIDENCE_ANALYSIS_COMPLETED,
                step_name,
                evidence_analysis.dict(),
            )
        if graph_state.get("risk_analysis"):
            risk_analysis = RiskAnalysisSchema(**graph_state["risk_analysis"])
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.AI_RISK_ANALYSIS_COMPLETED,
                step_name,
                risk_analysis.dict(),
            )

        information_gaps = [
            gap if isinstance(gap, InformationGap) else InformationGap(**gap)
            for gap in graph_state.get("information_gaps", [])
        ]
        if information_gaps:
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.AI_INFORMATION_GAPS_IDENTIFIED,
                step_name,
                {
                    "investigation_required": graph_state.get("investigation_required", False),
                    "information_gaps": [gap.dict() for gap in information_gaps],
                },
            )

        tool_calls = [
            call if isinstance(call, ToolExecutionRecord) else ToolExecutionRecord(**call)
            for call in graph_state.get("previous_tool_calls", [])
        ]
        for tool_call in tool_calls:
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.AI_TOOL_EXECUTED,
                step_name,
                tool_call.dict(),
            )

        if graph_state.get("adjuster_briefing"):
            adjuster_briefing = AdjusterBriefingSchema(**graph_state["adjuster_briefing"])
            self.audit.record_event(
                workflow_run,
                WorkflowEventType.AI_ADJUSTER_BRIEFING_GENERATED,
                step_name,
                {
                    "briefing_summary": adjuster_briefing.briefing_summary,
                    "why_workflow_paused": adjuster_briefing.why_workflow_paused,
                    "recommended_adjuster_actions": adjuster_briefing.recommended_adjuster_actions,
                },
                adjuster_briefing=adjuster_briefing.dict(),
            )
        if graph_state.get("recommended_next_action"):
            recommended_next_action = NextActionRecommendation(**graph_state["recommended_next_action"])

        return {
            "graph_state": graph_state,
            "evidence_analysis": evidence_analysis,
            "risk_analysis": risk_analysis,
            "adjuster_briefing": adjuster_briefing,
            "recommended_next_action": recommended_next_action,
        }
