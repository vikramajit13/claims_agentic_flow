from app.enums import HumanDecision
from app.models.claim import Claim
from app.models.claim_document import ClaimDocument
from app.models.human_task import HumanTask, HumanTaskPriority, HumanTaskType
from app.repositories.human_task_repository import HumanTaskRepository
from app.schemas.human_task_schema import HumanTaskDetailResponse, HumanTaskListItem, HumanTaskRecommendationView
from app.schemas.workflow_schema import AdjudicationRecommendation


class HumanTaskService:
    def __init__(self, task_repo: HumanTaskRepository | None = None) -> None:
        self.task_repo = task_repo or HumanTaskRepository()

    def create_task(
        self,
        claim_id: int,
        workflow_run_id: int,
        recommendation: AdjudicationRecommendation,
        task_type: HumanTaskType = HumanTaskType.CLAIM_REVIEW,
        priority: HumanTaskPriority = HumanTaskPriority.HIGH,
        assigned_to: str | None = None,
        created_reason: str | None = None,
        risk_factors: list[str] | None = None,
        adjuster_briefing: dict | None = None,
    ) -> HumanTask:
        return self.task_repo.create(
            claim_id=claim_id,
            workflow_run_id=workflow_run_id,
            task_type=task_type,
            priority=priority,
            assigned_to=assigned_to,
            created_reason=created_reason or recommendation.reason,
            risk_factors=risk_factors or recommendation.risk_factors,
            recommended_decision=recommendation.recommendation.value,
            recommended_payout_amount=recommendation.recommended_amount,
            adjuster_briefing=adjuster_briefing,
        )

    def assign_task(self, task_id: int, assigned_to: str) -> HumanTask:
        return self.task_repo.assign(task_id, assigned_to)

    def complete_task(
        self,
        task_id: int,
        decision: HumanDecision,
        decision_notes: str | None,
        completed_by: str,
        approved_amount: float | None,
    ) -> HumanTask:
        return self.task_repo.complete(task_id, decision, decision_notes, completed_by, approved_amount)

    def list_tasks(self) -> list[HumanTask]:
        return self.task_repo.list()

    def get_task(self, task_id: int) -> HumanTask:
        return self.task_repo.get(task_id)

    def build_task_list_item(self, task: HumanTask, claim: Claim) -> HumanTaskListItem:
        return HumanTaskListItem(
            task_id=task.id,
            claim_id=task.claim_id,
            claim_number=claim.claim_number,
            task_type=task.task_type.value,
            priority=task.priority.value,
            status=task.status.value,
            created_reason=task.created_reason,
            risk_factors=task.risk_factors,
            recommended_payout_amount=task.recommended_payout_amount,
            created_at=task.created_at,
        )

    def build_task_detail(self, task: HumanTask, claim: Claim, documents: list[ClaimDocument]) -> HumanTaskDetailResponse:
        return HumanTaskDetailResponse(
            task_id=task.id,
            task_type=task.task_type.value,
            status=task.status.value,
            priority=task.priority.value,
            claim=claim,
            risk_factors=task.risk_factors,
            documents=documents,
            recommendation=HumanTaskRecommendationView(
                system_decision=task.recommended_decision,
                recommended_payout_amount=task.recommended_payout_amount,
                reason=task.created_reason,
            ),
            adjuster_briefing=task.adjuster_briefing,
        )
