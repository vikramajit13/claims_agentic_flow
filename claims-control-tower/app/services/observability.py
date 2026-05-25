from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None

try:
    from langsmith import traceable as _traceable
except ModuleNotFoundError:  # pragma: no cover
    def _traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator


def configure_langsmith() -> None:
    if load_dotenv is None:
        return
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
