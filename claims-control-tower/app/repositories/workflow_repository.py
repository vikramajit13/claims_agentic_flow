from __future__ import annotations

from datetime import datetime

from app.database import get_store
from app.models.workflow_run import WorkflowRun, WorkflowRunStatus, WorkflowRunStep


class WorkflowRepository:
    def __init__(self) -> None:
        self.store = get_store()

    def create(self, claim_id: int, workflow_name: str = "claim_lifecycle") -> WorkflowRun:
        now = _now_iso()
        workflow_run = WorkflowRun(
            id=self.store.next_id("workflow_runs"),
            claim_id=claim_id,
            workflow_name=workflow_name,
            status=WorkflowRunStatus.RUNNING,
            current_step=WorkflowRunStep.CLAIM_INTAKE,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self.store.workflow_runs[workflow_run.id] = workflow_run
        return workflow_run

    def get(self, workflow_run_id: int) -> WorkflowRun:
        return self.store.workflow_runs[workflow_run_id]

    def list(self) -> list[WorkflowRun]:
        return list(self.store.workflow_runs.values())

    def update(self, workflow_run: WorkflowRun) -> WorkflowRun:
        self.store.workflow_runs[workflow_run.id] = workflow_run
        return workflow_run

    def update_status(self, workflow_run_id: int, status: WorkflowRunStatus, last_error: str | None = None) -> WorkflowRun:
        workflow_run = self.get(workflow_run_id)
        updated = workflow_run.copy(
            update={"status": status, "last_error": last_error, "updated_at": _now_iso()}
        )
        return self.update(updated)

    def update_step(self, workflow_run_id: int, step: WorkflowRunStep) -> WorkflowRun:
        workflow_run = self.get(workflow_run_id)
        updated = workflow_run.copy(update={"current_step": step, "updated_at": _now_iso()})
        return self.update(updated)

    def mark_waiting_for_human(self, workflow_run_id: int) -> WorkflowRun:
        return self.update_status(workflow_run_id, WorkflowRunStatus.WAITING_FOR_HUMAN)

    def mark_waiting_for_info(self, workflow_run_id: int) -> WorkflowRun:
        return self.update_status(workflow_run_id, WorkflowRunStatus.WAITING_FOR_INFO)

    def pause(self, workflow_run_id: int, reason: str | None = None) -> WorkflowRun:
        return self.update_status(workflow_run_id, WorkflowRunStatus.PAUSED, last_error=reason)

    def resume(self, workflow_run_id: int) -> WorkflowRun:
        workflow_run = self.get(workflow_run_id)
        updated = workflow_run.copy(update={"status": WorkflowRunStatus.RUNNING, "updated_at": _now_iso()})
        return self.update(updated)

    def complete(self, workflow_run_id: int) -> WorkflowRun:
        workflow_run = self.get(workflow_run_id)
        updated = workflow_run.copy(
            update={
                "status": WorkflowRunStatus.COMPLETED,
                "current_step": WorkflowRunStep.COMPLETED,
                "completed_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        )
        return self.update(updated)

    def fail(self, workflow_run_id: int, error_message: str) -> WorkflowRun:
        workflow_run = self.get(workflow_run_id)
        updated = workflow_run.copy(
            update={
                "status": WorkflowRunStatus.FAILED,
                "last_error": error_message,
                "updated_at": _now_iso(),
            }
        )
        return self.update(updated)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
