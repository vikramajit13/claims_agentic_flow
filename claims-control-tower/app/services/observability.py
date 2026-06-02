from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith import traceable as _traceable


def configure_langsmith() -> None:
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    os.environ.setdefault("LANGSMITH_TRACING", "false")


configure_langsmith()


def traceable(*args, **kwargs):
    return _traceable(*args, **kwargs)


@traceable(name="claims_review_graph", run_type="chain")
def run_claims_review_graph(graph, case_packet: Any) -> dict[str, Any]:
    return graph.invoke({"case_packet": case_packet})
