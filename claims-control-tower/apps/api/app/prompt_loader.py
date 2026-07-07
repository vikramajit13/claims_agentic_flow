from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml


PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"


@dataclass(frozen=True)
class PromptArtifact:
    name: str
    version: str
    role: str
    metadata: dict
    body: str
    path: Path


def _split_front_matter(content: str) -> tuple[dict, str]:
    if not content.startswith("---\n"):
        raise ValueError("Prompt file is missing YAML front matter.")

    _, remainder = content.split("---\n", 1)
    front_matter_raw, body = remainder.split("\n---\n", 1)
    metadata = yaml.safe_load(front_matter_raw) or {}
    return metadata, body.strip()


@lru_cache(maxsize=128)
def load_prompt_artifact(*, domain: str, role: str, version: str) -> PromptArtifact:
    path = PROMPTS_ROOT / domain / role / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    metadata, body = _split_front_matter(path.read_text())
    return PromptArtifact(
        name=metadata["prompt_name"],
        version=metadata["prompt_version"],
        role=metadata["prompt_role"],
        metadata=metadata,
        body=body,
        path=path,
    )


def render_prompt_template(template: str, variables: dict[str, object]) -> str:
    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
    return rendered
