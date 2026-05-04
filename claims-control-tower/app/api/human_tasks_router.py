
from fastapi import APIRouter

router = APIRouter(
    prefix="/v1",
    tags=["human_tasks"]
)

@router.get("/human-tasks")
async def get_human_tasks():
    # Logic to retrieve human tasks from the database or other source
    tasks = [
        {"id": 1, "name": "Review Claim", "status": "pending"},
        {"id": 2, "name": "Approve Payment", "status": "completed"},
    ]
    return tasks

@router.get("/human-tasks/{task_id}")
async def get_human_task(task_id: int):
    # Logic to retrieve a specific human task by ID from the database or other source
    task = {"id": task_id, "name": "Review Claim", "status": "pending"}
    return task

@router.post("/human-tasks/{task_id}/complete")
async def complete_human_task(task_id: int):
    # Logic to mark a human task as complete in the database or other source
    return {"message": f"Task {task_id} completed"}