from __future__ import annotations

from datetime import datetime

from app.database import get_store
from app.enums import HumanDecision
from app.models.human_task import HumanTask, HumanTaskPriority, HumanTaskStatus, HumanTaskType


class HumanTaskRepository:
    def __init__(self) -> None:
        self.store = get_store()

    def create(
        self,
        claim_id: int,
        workflow_run_id: int,
        task_type: HumanTaskType,
        priority: HumanTaskPriority,
        assigned_to: str | None,
        created_reason: str,
        risk_factors: list[str],
        recommended_decision: str | None,
        recommended_payout_amount: float | None,
        adjuster_briefing: dict | None = None,
    ) -> HumanTask:
        now = _now_iso()
        task = HumanTask(
            id=self.store.next_id("human_tasks"),
            claim_id=claim_id,
            workflow_run_id=workflow_run_id,
            task_type=task_type,
            status=HumanTaskStatus.OPEN,
            priority=priority,
            assigned_to=assigned_to,
            created_reason=created_reason,
            risk_factors=risk_factors,
            recommended_decision=recommended_decision,
            recommended_payout_amount=recommended_payout_amount,
            adjuster_briefing=adjuster_briefing,
            created_at=now,
            updated_at=now,
        )
        self.store.human_tasks[task.id] = task
        return task

    def get(self, task_id: int) -> HumanTask:
        return self.store.human_tasks[task_id]

    def list(self) -> list[HumanTask]:
        return list(self.store.human_tasks.values())

    def list_open(self) -> list[HumanTask]:
        return [task for task in self.list() if task.status != HumanTaskStatus.COMPLETED]

    def get_open_by_workflow(self, workflow_run_id: int) -> HumanTask | None:
        for task in self.list():
            if task.workflow_run_id == workflow_run_id and task.status != HumanTaskStatus.COMPLETED:
                return task
        return None

    def update(self, task: HumanTask) -> HumanTask:
        self.store.human_tasks[task.id] = task
        return task

    def assign(self, task_id: int, assigned_to: str) -> HumanTask:
        task = self.get(task_id)
        updated = task.copy(
            update={
                "assigned_to": assigned_to,
                "status": HumanTaskStatus.IN_PROGRESS,
                "updated_at": _now_iso(),
            }
        )
        return self.update(updated)

    def complete(
        self,
        task_id: int,
        decision: HumanDecision,
        decision_notes: str | None,
        completed_by: str,
        approved_amount: float | None,
    ) -> HumanTask:
        task = self.get(task_id)
        updated = task.copy(
            update={
                "status": HumanTaskStatus.COMPLETED,
                "reviewer_decision": decision,
                "reviewer_notes": decision_notes,
                "reviewer_modified_payout_amount": approved_amount if decision == HumanDecision.MODIFY_PAYOUT else None,
                "completed_by": completed_by,
                "updated_at": _now_iso(),
                "completed_at": _now_iso(),
            }
        )
        return self.update(updated)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
