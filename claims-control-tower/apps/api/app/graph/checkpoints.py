from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langgraph.checkpoint.memory import MemorySaver


class CheckpointStore(Protocol):
    def build(self):
        """Return a LangGraph checkpointer or None."""


@dataclass(frozen=True)
class MemoryCheckpointStore:
    def build(self):
        return MemorySaver()


@dataclass(frozen=True)
class NoCheckpointStore:
    def build(self):
        return None
