from __future__ import annotations

from datetime import datetime

from app.database import get_store
from app.models.workflow_event import ActorType, WorkflowEvent, WorkflowEventType
from app.models.workflow_run import WorkflowRun


class AuditService:
    def __init__(self) -> None:
        self.store = get_store()

    def record_event(
        self,
        workflow_run: WorkflowRun,
        event_type: WorkflowEventType,
        step_name: str,
        payload: dict,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: str = "workflow_engine",
        adjuster_briefing: dict | None = None,
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            id=self.store.next_id("workflow_events"),
            workflow_run_id=workflow_run.id,
            claim_id=workflow_run.claim_id,
            event_type=event_type,
            step_name=step_name,
            actor_type=actor_type,
            actor_id=actor_id,
            adjuster_briefing=adjuster_briefing,
            event_payload=payload,
            created_at=_now_iso(),
        )
        self.store.workflow_events[event.id] = event
        return event

    def record_step_started(
        self, workflow_run: WorkflowRun, step_name: str
    ) -> WorkflowEvent:
        return self.record_event(
            workflow_run,
            WorkflowEventType.STEP_STARTED,
            step_name,
            {"status": "started"},
        )

    def record_step_completed(
        self, workflow_run: WorkflowRun, step_name: str, payload: dict
    ) -> WorkflowEvent:
        return self.record_event(
            workflow_run, WorkflowEventType.STEP_COMPLETED, step_name, payload
        )

    def record_step_failed(
        self, workflow_run: WorkflowRun, step_name: str, error_message: str
    ) -> WorkflowEvent:
        return self.record_event(
            workflow_run,
            WorkflowEventType.STEP_FAILED,
            step_name,
            {"error": error_message},
        )

    def get_claim_audit(self, claim_id: int) -> list[WorkflowEvent]:
        return [
            event
            for event in self.store.workflow_events.values()
            if event.claim_id == claim_id
        ]

    def get_workflow_events(self, workflow_run_id: int) -> list[WorkflowEvent]:
        return [
            event
            for event in self.store.workflow_events.values()
            if event.workflow_run_id == workflow_run_id
        ]


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
