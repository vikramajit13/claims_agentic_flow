from __future__ import annotations

from contextlib import contextmanager
import time

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import OperationalError

from app.config import settings


class Base(DeclarativeBase):
    pass


database_url = settings.database_url
engine_kwargs = {"future": True}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class ClaimRecord(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, index=True)
    claim_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    claim_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True))


class ClaimDocumentRecord(Base):
    __tablename__ = "claim_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(Integer, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    s3_uri: Mapped[str] = mapped_column(String(1024))
    s3_bucket: Mapped[str] = mapped_column(String(255))
    s3_key: Mapped[str] = mapped_column(String(1024))
    upload_status: Mapped[str] = mapped_column(String(50), index=True)
    ocr_status: Mapped[str] = mapped_column(String(50), index=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_vector: Mapped[list[float] | None] = mapped_column(
        Vector(8) if engine.dialect.name == "postgresql" else JSON,
        nullable=True,
    )
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True))


class WorkflowRunRecord(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    current_step: Mapped[str] = mapped_column(String(50))
    hitl_required: Mapped[bool] = mapped_column()
    next_action: Mapped[str] = mapped_column(Text)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True))


def init_db() -> None:
    attempts = 10 if engine.dialect.name == "postgresql" else 1
    last_error = None
    for attempt in range(attempts):
        try:
            with engine.begin() as connection:
                if engine.dialect.name == "postgresql":
                    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                Base.metadata.create_all(bind=connection)
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(2)
    if last_error is not None:
        raise last_error


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
