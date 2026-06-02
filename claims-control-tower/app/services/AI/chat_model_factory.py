from __future__ import annotations

import os
from langchain_openai import ChatOpenAI


def create_langchain_chat_model():
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    openai_base_url = (
        f"{ollama_base_url}/v1"
        if not ollama_base_url.endswith("/v1")
        else ollama_base_url
    )
    return ChatOpenAI(
        model=ollama_model,
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        base_url=openai_base_url,
        temperature=0,
    )
