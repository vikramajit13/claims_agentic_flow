from __future__ import annotations

import os
from dataclasses import dataclass


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Claims Control Tower API"
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://claims:claims@postgres:5432/claims_control_tower",
    )
    aws_region: str = os.getenv("AWS_REGION", "ap-southeast-2")
    s3_bucket_default: str = os.getenv("S3_BUCKET_DEFAULT", "mock-claims-documents")
    s3_presign_expiry_seconds: int = int(os.getenv("S3_PRESIGN_EXPIRY_SECONDS", "900"))
    ocr_queue_url: str | None = os.getenv("OCR_QUEUE_URL")
    internal_service_token: str | None = os.getenv("INTERNAL_SERVICE_TOKEN")
    use_mock_s3: bool = _env_flag("USE_MOCK_S3", False)
    use_mock_ocr: bool = _env_flag("USE_MOCK_OCR", True)
    use_mock_sqs: bool = _env_flag("USE_MOCK_SQS", True)
    default_hitl_required: bool = _env_flag("DEFAULT_HITL_REQUIRED", True)


settings = Settings()
