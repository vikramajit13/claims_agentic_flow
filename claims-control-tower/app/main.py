from fastapi import FastAPI

from app.api.audit_router import router as audit_router
from app.api.claims_router import router as claims_router
from app.api.human_tasks_router import router as human_tasks_router
from app.api.payments_router import router as payments_router
from app.api.workflow_router import router as workflow_router
from app.config import settings
from app.services.observability import configure_langsmith

configure_langsmith()
app = FastAPI(title=settings.app_name)

app.include_router(claims_router)
app.include_router(workflow_router)
app.include_router(human_tasks_router)
app.include_router(payments_router)
app.include_router(audit_router)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
