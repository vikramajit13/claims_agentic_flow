from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    CheckpointTuple,
    PendingWrite,
    RunnableConfig,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

from app.db import GraphCheckpointRecord, GraphCheckpointWriteRecord, get_session

ALLOWLISTED_CHECKPOINT_TYPES = {
    ("app.graph.state", "ClaimGraphState"),
    ("app.schemas.document", "ClaimDocumentState"),
    ("app.schemas.workflow", "ClaimWorkflowState"),
}


class CheckpointStore(Protocol):
    def build(self):
        """Return a LangGraph checkpointer."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _encode_typed(value: Any) -> dict[str, str]:
    type_name, payload = BaseCheckpointSaver.serde.dumps_typed(value)
    return {
        "type": type_name,
        "payload": base64.b64encode(payload).decode("ascii"),
    }


def _decode_typed(value: dict[str, str]) -> Any:
    return BaseCheckpointSaver.serde.loads_typed(
        (value["type"], base64.b64decode(value["payload"].encode("ascii")))
    )


class PostgresCheckpointSaver(BaseCheckpointSaver[str]):
    def __init__(self) -> None:
        super().__init__()

    def _run_sync(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError("Use the async graph API with the Postgres checkpoint saver.")

    @staticmethod
    def _pending_write_to_dict(write: PendingWrite) -> dict[str, Any]:
        task_id, channel, value = write
        return {
            "task_id": task_id,
            "channel": channel,
            "value": _encode_typed(value),
        }

    @staticmethod
    def _dict_to_pending_write(row: dict[str, Any]) -> PendingWrite:
        return row["task_id"], row["channel"], _decode_typed(row["value"])

    async def _read_pending_writes(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> list[PendingWrite]:
        async with get_session() as session:
            rows = (
                (
                    await session.execute(
                        GraphCheckpointWriteRecord.__table__.select().where(
                            GraphCheckpointWriteRecord.thread_id == thread_id,
                            GraphCheckpointWriteRecord.checkpoint_ns == checkpoint_ns,
                            GraphCheckpointWriteRecord.checkpoint_id == checkpoint_id,
                        ).order_by(GraphCheckpointWriteRecord.write_idx.asc())
                    )
                )
                .mappings()
                .all()
            )
            return [(row["task_id"], row["channel"], _decode_typed(row["value"])) for row in rows]

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        async with get_session() as session:
            query = GraphCheckpointRecord.__table__.select().where(
                GraphCheckpointRecord.thread_id == thread_id,
                GraphCheckpointRecord.checkpoint_ns == checkpoint_ns,
            )
            if checkpoint_id:
                query = query.where(GraphCheckpointRecord.checkpoint_id == checkpoint_id)
            else:
                query = query.order_by(
                    GraphCheckpointRecord.id.desc(),
                    GraphCheckpointRecord.created_at.desc(),
                )

            row = (await session.execute(query)).mappings().first()
            if row is None:
                return None

            checkpoint = _decode_typed(row["checkpoint"])
            metadata = _decode_typed(row["checkpoint_metadata"])
            pending_writes = [
                self._dict_to_pending_write(entry) for entry in (row["pending_writes"] or [])
            ]
            parent_config = (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["parent_checkpoint_id"],
                    }
                }
                if row["parent_checkpoint_id"]
                else None
            )
            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes,
            )

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self._run_sync(self.aget_tuple(config))

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        async with get_session() as session:
            query = GraphCheckpointRecord.__table__.select()
            if config:
                query = query.where(GraphCheckpointRecord.thread_id == config["configurable"]["thread_id"])
                checkpoint_ns = config["configurable"].get("checkpoint_ns")
                if checkpoint_ns is not None:
                    query = query.where(GraphCheckpointRecord.checkpoint_ns == checkpoint_ns)
                checkpoint_id = get_checkpoint_id(config)
                if checkpoint_id:
                    query = query.where(GraphCheckpointRecord.checkpoint_id == checkpoint_id)
            if before and (before_checkpoint_id := get_checkpoint_id(before)):
                query = query.where(GraphCheckpointRecord.checkpoint_id < before_checkpoint_id)

            query = query.order_by(GraphCheckpointRecord.id.desc())
            rows = (await session.execute(query)).mappings().all()
            remaining = limit
            for row in rows:
                metadata = _decode_typed(row["checkpoint_metadata"])
                if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                    continue
                if remaining is not None:
                    if remaining <= 0:
                        break
                    remaining -= 1
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": row["thread_id"],
                            "checkpoint_ns": row["checkpoint_ns"],
                            "checkpoint_id": row["checkpoint_id"],
                        }
                    },
                    checkpoint=_decode_typed(row["checkpoint"]),
                    metadata=metadata,
                    parent_config=(
                        {
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_ns": row["checkpoint_ns"],
                                "checkpoint_id": row["parent_checkpoint_id"],
                            }
                        }
                        if row["parent_checkpoint_id"]
                        else None
                    ),
                    pending_writes=[
                        self._dict_to_pending_write(entry) for entry in (row["pending_writes"] or [])
                    ],
                )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        return self._run_sync(self._list(config, filter=filter, before=before, limit=limit))

    async def _list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        items = []
        async for item in self.alist(config, filter=filter, before=before, limit=limit):
            items.append(item)
        return items

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, Any],
    ) -> RunnableConfig:
        del new_versions
        checkpoint_metadata = get_checkpoint_metadata(config, metadata)
        checkpoint_id = checkpoint["id"]
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        pending_writes = await self._read_pending_writes(thread_id, checkpoint_ns, checkpoint_id)

        async with get_session() as session:
            existing = (
                await session.execute(
                    GraphCheckpointRecord.__table__.select().where(
                        GraphCheckpointRecord.thread_id == thread_id,
                        GraphCheckpointRecord.checkpoint_ns == checkpoint_ns,
                        GraphCheckpointRecord.checkpoint_id == checkpoint_id,
                    )
                )
            ).mappings().first()
            payload = {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "parent_checkpoint_id": parent_checkpoint_id,
                "checkpoint": _encode_typed(checkpoint),
                "checkpoint_metadata": _encode_typed(checkpoint_metadata),
                "pending_writes": [self._pending_write_to_dict(write) for write in pending_writes],
                "created_at": _now(),
                "updated_at": _now(),
            }
            if existing is None:
                await session.execute(GraphCheckpointRecord.__table__.insert().values(**payload))
            else:
                await session.execute(
                    GraphCheckpointRecord.__table__.update()
                    .where(GraphCheckpointRecord.id == existing["id"])
                    .values(**payload)
                )
            await session.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put(
        self,
        config: RunnableConfig,
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, Any],
    ) -> RunnableConfig:
        return self._run_sync(self.aput(config, checkpoint, metadata, new_versions))

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        async with get_session() as session:
            await session.execute(
                GraphCheckpointWriteRecord.__table__.delete().where(
                    GraphCheckpointWriteRecord.thread_id == thread_id,
                    GraphCheckpointWriteRecord.checkpoint_ns == checkpoint_ns,
                    GraphCheckpointWriteRecord.checkpoint_id == checkpoint_id,
                    GraphCheckpointWriteRecord.task_id == task_id,
                )
            )
            for idx, (channel, value) in enumerate(writes):
                await session.execute(
                    GraphCheckpointWriteRecord.__table__.insert().values(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        checkpoint_id=checkpoint_id,
                        task_id=task_id,
                        task_path=task_path,
                        write_idx=idx,
                        channel=channel,
                        value=_encode_typed(value),
                        created_at=_now(),
                        updated_at=_now(),
                    )
                )
            checkpoint_row = (
                await session.execute(
                    GraphCheckpointRecord.__table__.select().where(
                        GraphCheckpointRecord.thread_id == thread_id,
                        GraphCheckpointRecord.checkpoint_ns == checkpoint_ns,
                        GraphCheckpointRecord.checkpoint_id == checkpoint_id,
                    )
                )
            ).mappings().first()
            if checkpoint_row is not None:
                await session.execute(
                    GraphCheckpointRecord.__table__.update()
                    .where(GraphCheckpointRecord.id == checkpoint_row["id"])
                    .values(
                        pending_writes=[
                            self._pending_write_to_dict((task_id, channel, value))
                            for channel, value in writes
                        ],
                        updated_at=_now(),
                    )
                )
            await session.commit()

    def put_writes(
        self,
        config: RunnableConfig,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return self._run_sync(self.aput_writes(config, writes, task_id, task_path))

    async def adelete_thread(self, thread_id: str) -> None:
        async with get_session() as session:
            await session.execute(
                GraphCheckpointWriteRecord.__table__.delete().where(
                    GraphCheckpointWriteRecord.thread_id == thread_id
                )
            )
            await session.execute(
                GraphCheckpointRecord.__table__.delete().where(GraphCheckpointRecord.thread_id == thread_id)
            )
            await session.commit()

    def delete_thread(self, thread_id: str) -> None:
        return self._run_sync(self.adelete_thread(thread_id))

    async def adelete_for_runs(self, run_ids) -> None:
        for run_id in run_ids:
            await self.adelete_thread(run_id)

    def delete_for_runs(self, run_ids) -> None:
        return self._run_sync(self.adelete_for_runs(run_ids))

    async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        async with get_session() as session:
            checkpoints = (
                await session.execute(
                    GraphCheckpointRecord.__table__.select().where(
                        GraphCheckpointRecord.thread_id == source_thread_id
                    )
                )
            ).mappings().all()
            writes = (
                await session.execute(
                    GraphCheckpointWriteRecord.__table__.select().where(
                        GraphCheckpointWriteRecord.thread_id == source_thread_id
                    )
                )
            ).mappings().all()
            for row in checkpoints:
                await session.execute(
                    GraphCheckpointRecord.__table__.insert().values(
                        thread_id=target_thread_id,
                        checkpoint_ns=row["checkpoint_ns"],
                        checkpoint_id=row["checkpoint_id"],
                        parent_checkpoint_id=row["parent_checkpoint_id"],
                        checkpoint=row["checkpoint"],
                        checkpoint_metadata=row["checkpoint_metadata"],
                        pending_writes=row["pending_writes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            for row in writes:
                await session.execute(
                    GraphCheckpointWriteRecord.__table__.insert().values(
                        thread_id=target_thread_id,
                        checkpoint_ns=row["checkpoint_ns"],
                        checkpoint_id=row["checkpoint_id"],
                        task_id=row["task_id"],
                        task_path=row["task_path"],
                        write_idx=row["write_idx"],
                        channel=row["channel"],
                        value=row["value"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            await session.commit()

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        return self._run_sync(self.acopy_thread(source_thread_id, target_thread_id))

    async def aprune(self, thread_ids, *, strategy: str = "keep_latest") -> None:
        if strategy == "delete":
            for thread_id in thread_ids:
                await self.adelete_thread(thread_id)
            return

        async with get_session() as session:
            for thread_id in thread_ids:
                rows = (
                    await session.execute(
                        GraphCheckpointRecord.__table__.select().where(
                            GraphCheckpointRecord.thread_id == thread_id
                        )
                    )
                ).mappings().all()
                by_ns: dict[str, list[dict[str, Any]]] = {}
                for row in rows:
                    by_ns.setdefault(row["checkpoint_ns"], []).append(row)
                for checkpoint_ns, ns_rows in by_ns.items():
                    if not ns_rows:
                        continue
                    latest = max(ns_rows, key=lambda row: row["id"])
                    for row in ns_rows:
                        if row["id"] == latest["id"]:
                            continue
                        await session.execute(
                            GraphCheckpointWriteRecord.__table__.delete().where(
                                GraphCheckpointWriteRecord.thread_id == thread_id,
                                GraphCheckpointWriteRecord.checkpoint_ns == checkpoint_ns,
                                GraphCheckpointWriteRecord.checkpoint_id == row["checkpoint_id"],
                            )
                        )
                        await session.execute(
                            GraphCheckpointRecord.__table__.delete().where(
                                GraphCheckpointRecord.id == row["id"]
                            )
                        )
            await session.commit()

    def prune(self, thread_ids, *, strategy: str = "keep_latest") -> None:
        return self._run_sync(self.aprune(thread_ids, strategy=strategy))


@dataclass(frozen=True)
class PostgresCheckpointStore:
    def build(self):
        return PostgresCheckpointSaver().with_allowlist(ALLOWLISTED_CHECKPOINT_TYPES)
