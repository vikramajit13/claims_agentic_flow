from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.graph.builder import (
    CLAIM_INVESTIGATION_GRAPH,
    CLAIM_REVIEW_GRAPH,
    CUSTOMER_HISTORY_GRAPH,
    DOCUMENT_EVIDENCE_GRAPH,
    GraphBuilder,
    GraphDefinition,
)
from app.graph.checkpoints import PostgresCheckpointStore
from app.graph.runtime import GraphRuntime, GraphRuntimeConfig


@dataclass(frozen=True)
class GraphStateManagerConfig:
    graph_name: str
    graph_version: str
    builder_factory: type[GraphBuilder]
    debug: bool = False
    checkpoint_backend: str = "postgres"
    interrupt_before: tuple[str, ...] = field(default_factory=tuple)
    interrupt_after: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GraphStateManagerFactoryConfig:
    graph_key: str = "claim_review"
    debug: bool = False
    checkpoint_backend: str = "postgres"
    interrupt_before: tuple[str, ...] = field(default_factory=tuple)
    interrupt_after: tuple[str, ...] = field(default_factory=tuple)


class GraphStateManager:
    def __init__(self, config: GraphStateManagerConfig, runtime_cls: type[GraphRuntime], config_cls: type[GraphRuntimeConfig]) -> None:
        self.config = config
        checkpoint_store = self._build_checkpoint_store(config.checkpoint_backend)
        self.runtime = runtime_cls(
            builder=config.builder_factory(),
            checkpoint_store=checkpoint_store,
            config=config_cls(
                graph_name=config.graph_name,
                graph_version=config.graph_version,
                debug=config.debug,
                interrupt_before=config.interrupt_before,
                interrupt_after=config.interrupt_after,
            ),
        )

    @staticmethod
    def _build_checkpoint_store(backend: str):
        if backend != "postgres":
            raise ValueError(f"Unsupported checkpoint_backend: {backend}")
        return PostgresCheckpointStore()

    def compile(self):
        return self.runtime.compiled()

    def invoke(self, initial_state, *, thread_id: str | None = None):
        return self.runtime.invoke(initial_state, thread_id=thread_id)

    async def ainvoke(self, initial_state, *, thread_id: str | None = None):
        return await self.runtime.ainvoke(initial_state, thread_id=thread_id)


class GraphStateManagerFactory:
    GRAPH_REGISTRY: dict[str, GraphDefinition] = {
        "claim_review": CLAIM_REVIEW_GRAPH,
        "claim_investigation": CLAIM_INVESTIGATION_GRAPH,
        "customer_history": CUSTOMER_HISTORY_GRAPH,
        "document_evidence": DOCUMENT_EVIDENCE_GRAPH,
    }

    def __init__(self, config: GraphStateManagerFactoryConfig | None = None) -> None:
        self.config = config or GraphStateManagerFactoryConfig()

    @classmethod
    def get_definition(cls, graph_key: str) -> GraphDefinition:
        try:
            return cls.GRAPH_REGISTRY[graph_key]
        except KeyError as exc:
            available = ", ".join(sorted(cls.GRAPH_REGISTRY))
            raise ValueError(f"Unknown graph_key '{graph_key}'. Available graph keys: {available}") from exc

    def create(self) -> GraphStateManager:
        definition = self.get_definition(self.config.graph_key)
        return GraphStateManager(
            GraphStateManagerConfig(
                graph_name=definition.name,
                graph_version=definition.version,
                builder_factory=definition.builder_factory,
                debug=self.config.debug,
                checkpoint_backend=self.config.checkpoint_backend,
                interrupt_before=self.config.interrupt_before,
                interrupt_after=self.config.interrupt_after,
            ),
            runtime_cls=GraphRuntime,
            config_cls=GraphRuntimeConfig,
        )


def build_claim_graph():
    return GraphStateManagerFactory(
        GraphStateManagerFactoryConfig(graph_key="claim_review")
    ).create().runtime.compiled()

def build_investigation_graph():
    return GraphStateManagerFactory(
        GraphStateManagerFactoryConfig(graph_key="claim_investigation")
    ).create().runtime.compiled()


def build_customer_history_graph():
    return GraphStateManagerFactory(
        GraphStateManagerFactoryConfig(graph_key="customer_history")
    ).create().runtime.compiled()


def build_document_evidence_graph():
    return GraphStateManagerFactory(
        GraphStateManagerFactoryConfig(graph_key="document_evidence")
    ).create().runtime.compiled()


ClaimGraphRuntime = GraphRuntime
