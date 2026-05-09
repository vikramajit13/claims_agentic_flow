from app.models.human_task import HumanTask, HumanTaskType
from app.repositories.human_task_repository import HumanTaskRepository
from app.schemas.workflow_schema import AdjudicationRecommendation


class HumanTaskService:
    def __init__(self, task_repo: HumanTaskRepository | None = None) -> None:
        self.task_repo = task_repo or HumanTaskRepository()

    def create_task(
        self,
        claim_id: int,
        workflow_run_id: int,
        recommendation: AdjudicationRecommendation,
    ) -> HumanTask:
        task_type = (
            HumanTaskType.MISSING_DOCUMENT_REVIEW
            if recommendation.recommendation.value == "REQUEST_MORE_INFO"
            else HumanTaskType.FRAUD_REVIEW
        )
        return self.task_repo.create(
            claim_id=claim_id,
            workflow_run_id=workflow_run_id,
            task_type=task_type,
            assigned_to="claims_reviewer_queue",
            reason=recommendation.reason,
        )

    def complete_task(self, task_id: int, decision: str, decision_notes: str | None) -> HumanTask:
        return self.task_repo.complete(task_id, decision, decision_notes)

    def list_tasks(self) -> list[HumanTask]:
        return self.task_repo.list()

    def get_task(self, task_id: int) -> HumanTask:
        return self.task_repo.get(task_id)
