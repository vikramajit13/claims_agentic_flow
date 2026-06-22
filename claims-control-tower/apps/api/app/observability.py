from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langsmith import traceable as _traceable


def configure_langsmith() -> None:
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    os.environ.setdefault("LANGSMITH_TRACING", "false")


configure_langsmith()


def traceable(*args, **kwargs):
    return _traceable(*args, **kwargs)
