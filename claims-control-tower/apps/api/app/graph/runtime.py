from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import uuid4

from app.graph.checkpoints import CheckpointStore, NoCheckpointStore
from app.graph.state import ClaimGraphState


@dataclass(frozen=True)
class GraphRuntimeConfig:
    graph_name: str
    graph_version: str
    debug: bool = False
    interrupt_before: tuple[str, ...] = ()
    interrupt_after: tuple[str, ...] = ()


class ClaimGraphRuntime:
    def __init__(self, *, builder, checkpoint_store: CheckpointStore | None, config: GraphRuntimeConfig) -> None:
        self.builder = builder
        self.checkpoint_store = checkpoint_store or NoCheckpointStore()
        self.config = config

    @lru_cache(maxsize=1)
    def compiled(self):
        workflow = self.builder.build()
        compile_kwargs: dict[str, Any] = {
            "debug": self.config.debug,
            "interrupt_before": list(self.config.interrupt_before),
            "interrupt_after": list(self.config.interrupt_after),
        }
        checkpointer = self.checkpoint_store.build()
        if checkpointer is not None:
            compile_kwargs["checkpointer"] = checkpointer
        return workflow.compile(**compile_kwargs)

    def invoke(self, initial_state: ClaimGraphState | dict[str, Any], *, thread_id: str | None = None) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.ainvoke(initial_state, thread_id=thread_id))
        raise RuntimeError("ClaimGraphRuntime.invoke() cannot be used from an async context; use ainvoke() instead.")

    async def ainvoke(self, initial_state: ClaimGraphState | dict[str, Any], *, thread_id: str | None = None) -> Any:
        derived_thread_id = thread_id
        if derived_thread_id is None:
            if isinstance(initial_state, dict):
                derived_thread_id = initial_state.get("correlation_id")
            else:
                derived_thread_id = initial_state.correlation_id
        if derived_thread_id is None:
            derived_thread_id = f"{self.config.graph_name}-{uuid4()}"

        if isinstance(initial_state, dict):
            graph_input = {
                "graph_name": self.config.graph_name,
                "graph_version": self.config.graph_version,
                "graph_run_id": derived_thread_id,
                **initial_state,
            }
        else:
            graph_input = initial_state.model_copy(
                update={
                    "graph_name": self.config.graph_name,
                    "graph_version": self.config.graph_version,
                    "graph_run_id": derived_thread_id,
                }
            )

        return await self.compiled().ainvoke(
            graph_input,
            config={"configurable": {"thread_id": derived_thread_id}},
        )
