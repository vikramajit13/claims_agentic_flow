from __future__ import annotations

from langsmith import Client

from app.observability import traceable
from app.prompt_loader import PromptArtifact


class LangSmithPromptRegistry:
    def __init__(self, client: Client | None = None) -> None:
        self.client = client or Client()

    @traceable(name="push_prompt_to_langsmith", run_type="tool")
    def push_markdown_prompt(
        self,
        *,
        prompt_identifier: str,
        artifact: PromptArtifact,
        description: str | None = None,
        tags: list[str] | None = None,
        is_public: bool = False,
    ) -> str:
        object_payload = {
            "prompt_name": artifact.name,
            "prompt_version": artifact.version,
            "prompt_role": artifact.role,
            "metadata": artifact.metadata,
            "body": artifact.body,
            "path": str(artifact.path),
        }
        return self.client.push_prompt(
            prompt_identifier,
            object=object_payload,
            is_public=is_public,
            description=description or artifact.metadata.get("change_reason"),
            tags=tags or [
                f"domain:{artifact.metadata.get('domain', 'unknown')}",
                f"task:{artifact.metadata.get('task', 'unknown')}",
                f"version:{artifact.version}",
                f"role:{artifact.role}",
            ],
            commit_description=artifact.metadata.get("change_reason"),
        )
