from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langsmith import traceable as _traceable


def configure_langsmith() -> None:
    resolved = Path(__file__).resolve()
    for parent in resolved.parents:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
            break
    os.environ.setdefault("LANGSMITH_TRACING", "false")


configure_langsmith()


def traceable(*args, **kwargs):
    return _traceable(*args, **kwargs)
