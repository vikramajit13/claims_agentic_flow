from __future__ import annotations

from datetime import datetime

from app.database import get_store
from app.models.human_task import HumanTask, HumanTaskStatus, HumanTaskType


class HumanTaskRepository:
    def __init__(self) -> None:
        self.store = get_store()

    def create(
        self,
        claim_id: int,
        workflow_run_id: int,
        task_type: HumanTaskType,
        assigned_to: str,
        reason: str,
    ) -> HumanTask:
        task = HumanTask(
            id=self.store.next_id("human_tasks"),
            claim_id=claim_id,
            workflow_run_id=workflow_run_id,
            task_type=task_type,
            status=HumanTaskStatus.OPEN,
            assigned_to=assigned_to,
            reason=reason,
            created_at=_now_iso(),
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

    def complete(self, task_id: int, decision: str, decision_notes: str | None) -> HumanTask:
        task = self.get(task_id)
        updated = task.copy(
            update={
                "status": HumanTaskStatus.COMPLETED,
                "decision": decision,
                "decision_notes": decision_notes,
                "completed_at": _now_iso(),
            }
        )
        return self.update(updated)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
