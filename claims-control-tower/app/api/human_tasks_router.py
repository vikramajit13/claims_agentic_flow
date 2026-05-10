from fastapi import APIRouter, HTTPException, Query

from app.schemas.human_task_schema import (
    HumanTaskAssignRequest,
    HumanTaskCompletionResponse,
    HumanTaskDecisionRequest,
)
from app.services.claim_service import ClaimService
from app.services.human_task_service import HumanTaskService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/human-tasks", tags=["human_tasks"])
task_service = HumanTaskService()
workflow_service = WorkflowService()
claim_service = ClaimService()


@router.get("")
def get_human_tasks(
    status: str | None = Query(default=None),
    task_type: str | None = Query(default=None),
    priority: str | None = Query(default=None),
):
    tasks = task_service.list_tasks()
    if status:
        tasks = [task for task in tasks if task.status.value == status.upper()]
    if task_type:
        tasks = [task for task in tasks if task.task_type.value == task_type.upper()]
    if priority:
        tasks = [task for task in tasks if task.priority.value == priority.upper()]
    return [
        task_service.build_task_list_item(task, claim_service.get_claim(task.claim_id))
        for task in tasks
    ]


@router.get("/{task_id}")
def get_human_task(task_id: int):
    try:
        task = task_service.get_task(task_id)
        claim = claim_service.get_claim(task.claim_id)
        documents = claim_service.get_claim_documents(task.claim_id)
        return task_service.build_task_detail(task, claim, documents)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human task not found") from exc


@router.post("/{task_id}/assign")
def assign_human_task(task_id: int, request: HumanTaskAssignRequest):
    try:
        return task_service.assign_task(task_id, request.assigned_to)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human task not found") from exc


@router.post("/{task_id}/complete", response_model=HumanTaskCompletionResponse)
def complete_human_task(task_id: int, request: HumanTaskDecisionRequest):
    try:
        task, workflow_result = workflow_service.complete_human_task(task_id, request)
        return HumanTaskCompletionResponse(task=task, workflow_result=workflow_result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
