from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.graph.builder import ClaimReviewGraphBuilder
from app.graph.checkpoints import DatabaseCheckpointStore, MemoryCheckpointStore, NoCheckpointStore
from app.graph.runtime import ClaimGraphRuntime, GraphRuntimeConfig


@dataclass(frozen=True)
class GraphStateManagerConfig:
    graph_name: str = "claim_review_graph"
    graph_version: str = "v1"
    debug: bool = False
    checkpoint_backend: str = settings.graph_checkpoint_backend
    interrupt_before: tuple[str, ...] = field(default_factory=tuple)
    interrupt_after: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GraphStateManagerFactoryConfig:
    graph_name: str = "claim_review_graph"
    graph_version: str = "v1"
    debug: bool = False
    checkpoint_backend: str = settings.graph_checkpoint_backend
    interrupt_before: tuple[str, ...] = field(default_factory=tuple)
    interrupt_after: tuple[str, ...] = field(default_factory=tuple)


class GraphStateManager:
    def __init__(self, config: GraphStateManagerConfig) -> None:
        self.config = config
        checkpoint_store = self._build_checkpoint_store(config.checkpoint_backend)
        self.runtime = ClaimGraphRuntime(
            builder=ClaimReviewGraphBuilder(),
            checkpoint_store=checkpoint_store,
            config=GraphRuntimeConfig(
                graph_name=config.graph_name,
                graph_version=config.graph_version,
                debug=config.debug,
                interrupt_before=config.interrupt_before,
                interrupt_after=config.interrupt_after,
            ),
        )

    @staticmethod
    def _build_checkpoint_store(backend: str):
        if backend in {"database", "persistent"}:
            return DatabaseCheckpointStore()
        if backend == "memory":
            return MemoryCheckpointStore()
        if backend == "none":
            return NoCheckpointStore()
        raise ValueError(f"Unsupported checkpoint_backend: {backend}")

    def compile(self):
        return self.runtime.compiled()

    def invoke(self, initial_state, *, thread_id: str | None = None):
        return self.runtime.invoke(initial_state, thread_id=thread_id)

    async def ainvoke(self, initial_state, *, thread_id: str | None = None):
        return await self.runtime.ainvoke(initial_state, thread_id=thread_id)


class GraphStateManagerFactory:
    def __init__(self, config: GraphStateManagerFactoryConfig | None = None) -> None:
        self.config = config or GraphStateManagerFactoryConfig()

    def create(self) -> GraphStateManager:
        return GraphStateManager(
            GraphStateManagerConfig(
                graph_name=self.config.graph_name,
                graph_version=self.config.graph_version,
                debug=self.config.debug,
                checkpoint_backend=self.config.checkpoint_backend,
                interrupt_before=self.config.interrupt_before,
                interrupt_after=self.config.interrupt_after,
            )
        )


def build_claim_graph():
    return GraphStateManagerFactory().create().runtime.compiled()
