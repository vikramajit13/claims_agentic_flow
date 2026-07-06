from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import init_db
from app.observability import configure_langsmith
from app.routers.claims import router as claims_router
from app.routers.workflows import router as workflows_router

configure_langsmith()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(claims_router)
app.include_router(workflows_router)


@app.get("/health")
async def healthcheck():
    return {"status": "ok", "env": settings.app_env}
