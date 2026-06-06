#!/usr/bin/env python3
from __future__ import annotations

import aws_cdk as cdk

from claims_agent_stack import ClaimsAgentStack


app = cdk.App()

stage = app.node.try_get_context("stage") or "prod"
ollama_base_url = app.node.try_get_context("ollamaBaseUrl") or "http://host.docker.internal:11434"
ollama_model = app.node.try_get_context("ollamaModel") or "llama3.1:8b"
langsmith_project = app.node.try_get_context("langsmithProject") or "claims-control-tower"
langsmith_api_key = app.node.try_get_context("langsmithApiKey") or ""

ClaimsAgentStack(
    app,
    f"ClaimsAgent-{stage.capitalize()}-Sydney",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "ap-southeast-2",
    ),
    stage=stage,
    ollama_base_url=ollama_base_url,
    ollama_model=ollama_model,
    langsmith_project=langsmith_project,
    langsmith_api_key=langsmith_api_key,
)

app.synth()

