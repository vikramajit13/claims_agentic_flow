import json
import logging
from typing import Any
from urllib import error, request


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class OllamaAsyncService:
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.1:8b"):
        self.base_url = f"{base_url.rstrip('/')}/api/generate"
        self.default_model = default_model
        self.timeout_seconds = 30

    def generate_structured(self, prompt: str, fallback: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        payload = json.dumps(
            {
                "model": model or self.default_model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        req = request.Request(
            self.base_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
                raw_response = body.get("response", "").strip()
                if not raw_response:
                    return fallback
                return json.loads(raw_response)
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:  # pragma: no cover
            logging.warning("Falling back to local adjuster briefing generation: %s", exc)
            return fallback
