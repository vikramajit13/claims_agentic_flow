from fastapi import APIRouter, HTTPException

from app.schemas.human_task_schema import HumanTaskCompletionResponse, HumanTaskDecisionRequest
from app.services.human_task_service import HumanTaskService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/human-tasks", tags=["human_tasks"])
task_service = HumanTaskService()
workflow_service = WorkflowService()


@router.get("")
def get_human_tasks():
    return task_service.list_tasks()


@router.get("/{task_id}")
def get_human_task(task_id: int):
    try:
        return task_service.get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human task not found") from exc


@router.post("/{task_id}/complete", response_model=HumanTaskCompletionResponse)
def complete_human_task(task_id: int, request: HumanTaskDecisionRequest):
    try:
        task, workflow_result = workflow_service.complete_human_task(task_id, request)
        return HumanTaskCompletionResponse(task=task, workflow_result=workflow_result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Human task not found") from exc
