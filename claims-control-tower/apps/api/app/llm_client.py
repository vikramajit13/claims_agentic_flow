from __future__ import annotations

import json
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.observability import traceable


class LLMClient:
    def __init__(self) -> None:
        self.enabled = settings.enable_llm_document_intelligence and (
            bool(settings.openai_api_key) or self._is_local_keyless_llm_allowed()
        )

    def _is_local_keyless_llm_allowed(self) -> bool:
        if not settings.allow_keyless_local_llm:
            return False
        parsed = urlparse(settings.openai_base_url)
        host = (parsed.hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "host.docker.internal"}

    @traceable(name="document_intelligence_llm_call", run_type="llm")
    def create_document_intelligence(self, *, system_prompt: str, user_prompt: str) -> dict:
        if not self.enabled:
            raise RuntimeError("LLM document intelligence is not configured.")

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
