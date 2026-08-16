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
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    document_intelligence_model: str = os.getenv("DOCUMENT_INTELLIGENCE_MODEL", "gpt-4.1-mini")
    llm_judge_model: str = os.getenv("LLM_JUDGE_MODEL", os.getenv("DOCUMENT_INTELLIGENCE_MODEL", "gpt-4.1-mini"))
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    allow_keyless_local_llm: bool = _env_flag("ALLOW_KEYLESS_LOCAL_LLM", True)
    enable_llm_document_intelligence: bool = _env_flag("ENABLE_LLM_DOCUMENT_INTELLIGENCE", True)
    enable_llm_tool_selection_judge: bool = _env_flag("ENABLE_LLM_TOOL_SELECTION_JUDGE", False)
    enable_llm_action_judge: bool = _env_flag("ENABLE_LLM_ACTION_JUDGE", False)
    llm_judge_blocking_min_risk_score: int = int(os.getenv("LLM_JUDGE_BLOCKING_MIN_RISK_SCORE", "70"))
    llm_judge_advisory_max_risk_score: int = int(os.getenv("LLM_JUDGE_ADVISORY_MAX_RISK_SCORE", "39"))
    document_intelligence_min_confidence: float = float(os.getenv("DOCUMENT_INTELLIGENCE_MIN_CONFIDENCE", "0.7"))
    document_intelligence_prompt_version: str = os.getenv("DOCUMENT_INTELLIGENCE_PROMPT_VERSION", "v1")
    use_mock_s3: bool = _env_flag("USE_MOCK_S3", False)
    use_mock_ocr: bool = _env_flag("USE_MOCK_OCR", True)
    use_mock_sqs: bool = _env_flag("USE_MOCK_SQS", True)
    default_hitl_required: bool = _env_flag("DEFAULT_HITL_REQUIRED", True)


settings = Settings()
