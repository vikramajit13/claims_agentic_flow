from __future__ import annotations

import json
from urllib.parse import urlparse

import boto3
import httpx

from app.config import settings
from app.observability import traceable


class LLMClient:
    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self.enabled = settings.enable_llm_document_intelligence and self._is_provider_configured()
        self._bedrock_client = None

    def _is_provider_configured(self) -> bool:
        if self.provider == "bedrock":
            return bool(settings.bedrock_model_id)
        return bool(settings.openai_api_key) or self._is_local_keyless_llm_allowed()

    def _is_local_keyless_llm_allowed(self) -> bool:
        if not settings.allow_keyless_local_llm:
            return False
        parsed = urlparse(settings.openai_base_url)
        host = (parsed.hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "host.docker.internal"}

    def _get_bedrock_client(self):
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        return self._bedrock_client

    @traceable(name="document_intelligence_llm_call", run_type="llm")
    def create_document_intelligence(self, *, system_prompt: str, user_prompt: str) -> dict:
        if not self.enabled:
            raise RuntimeError("LLM document intelligence is not configured.")

        if self.provider == "bedrock":
            return self._create_document_intelligence_bedrock(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        headers = {
            "Content-Type": "application/json",
        }
        if settings.openai_api_key:
            headers["Authorization"] = f"Bearer {settings.openai_api_key}"

        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": settings.document_intelligence_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=45.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)

    def _create_document_intelligence_bedrock(self, *, system_prompt: str, user_prompt: str) -> dict:
        response = self._get_bedrock_client().converse(
            modelId=settings.bedrock_model_id,
            system=[{"text": system_prompt}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}],
                }
            ],
            inferenceConfig={
                "temperature": 0,
            },
        )
        output = response.get("output", {})
        message = output.get("message", {})
        parts = message.get("content", [])
        content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not content:
            raise RuntimeError("Bedrock returned an empty response.")
        return json.loads(content)
