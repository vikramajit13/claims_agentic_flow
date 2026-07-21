from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import delete, desc, select
from app.db import GraphCheckpointRecord, GraphCheckpointWriteRecord, SyncSessionLocal
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    CheckpointTuple,
    PendingWrite,
    RunnableConfig,
    get_checkpoint_id,
    get_checkpoint_metadata,
)
from langgraph.checkpoint.memory import MemorySaver

ALLOWLISTED_CHECKPOINT_TYPES = {
    ("app.graph.state", "ClaimGraphState"),
    ("app.schemas.document", "ClaimDocumentState"),
    ("app.schemas.workflow", "ClaimWorkflowState"),
}


class CheckpointStore(Protocol):
    def build(self):
        """Return a LangGraph checkpointer or None."""


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


class DatabaseCheckpointSaver(BaseCheckpointSaver[str]):
    def __init__(self) -> None:
        super().__init__()

    def _session(self):
        return SyncSessionLocal()

    def _encode_checkpoint_row(
        self,
        config: RunnableConfig,
        checkpoint: dict[str, Any],
        checkpoint_metadata: dict[str, Any],
    ) -> GraphCheckpointRecord:
        checkpoint_id = checkpoint["id"]
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        pending_writes = self._read_pending_writes(thread_id, checkpoint_ns, checkpoint_id)
        return GraphCheckpointRecord(
            thread_id=thread_id,
            checkpoint_ns=checkpoint_ns,
            checkpoint_id=checkpoint_id,
            parent_checkpoint_id=parent_checkpoint_id,
            checkpoint=_encode_typed(checkpoint),
            checkpoint_metadata=_encode_typed(checkpoint_metadata),
            pending_writes=[self._pending_write_to_dict(write) for write in pending_writes],
            created_at=_now(),
            updated_at=_now(),
        )

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

    def _read_pending_writes(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> list[PendingWrite]:
        with self._session() as session:
            rows = (
                session.execute(
                    select(GraphCheckpointWriteRecord).where(
                        GraphCheckpointWriteRecord.thread_id == thread_id,
                        GraphCheckpointWriteRecord.checkpoint_ns == checkpoint_ns,
                        GraphCheckpointWriteRecord.checkpoint_id == checkpoint_id,
                    ).order_by(GraphCheckpointWriteRecord.write_idx.asc())
                )
                .scalars()
                .all()
            )
            return [(row.task_id, row.channel, _decode_typed(row.value)) for row in rows]

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        with self._session() as session:
            query = select(GraphCheckpointRecord).where(
                GraphCheckpointRecord.thread_id == thread_id,
                GraphCheckpointRecord.checkpoint_ns == checkpoint_ns,
            )
            if checkpoint_id:
                query = query.where(GraphCheckpointRecord.checkpoint_id == checkpoint_id)
            else:
                query = query.order_by(
                    desc(GraphCheckpointRecord.id),
                    desc(GraphCheckpointRecord.created_at),
                )

            row = session.execute(query).scalars().first()
            if row is None:
                return None

            checkpoint = _decode_typed(row.checkpoint)
            metadata = _decode_typed(row.checkpoint_metadata)
            pending_writes = [
                self._dict_to_pending_write(entry) for entry in (row.pending_writes or [])
            ]
            parent_config = (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row.parent_checkpoint_id,
                    }
                }
                if row.parent_checkpoint_id
                else None
            )
            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row.checkpoint_id,
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes,
            )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ):
        with self._session() as session:
            query = select(GraphCheckpointRecord)
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

            query = query.order_by(desc(GraphCheckpointRecord.id))
            rows = session.execute(query).scalars().all()
            remaining = limit
            for row in rows:
                metadata = _decode_typed(row.checkpoint_metadata)
                if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                    continue
                if remaining is not None:
                    if remaining <= 0:
                        break
                    remaining -= 1
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": row.thread_id,
                            "checkpoint_ns": row.checkpoint_ns,
                            "checkpoint_id": row.checkpoint_id,
                        }
                    },
                    checkpoint=_decode_typed(row.checkpoint),
                    metadata=metadata,
                    parent_config=(
                        {
                            "configurable": {
                                "thread_id": row.thread_id,
                                "checkpoint_ns": row.checkpoint_ns,
                                "checkpoint_id": row.parent_checkpoint_id,
                            }
                        }
                        if row.parent_checkpoint_id
                        else None
                    ),
                    pending_writes=[
                        self._dict_to_pending_write(entry) for entry in (row.pending_writes or [])
                    ],
                )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, Any],
    ) -> RunnableConfig:
        del new_versions
        record = self._encode_checkpoint_row(config, checkpoint, get_checkpoint_metadata(config, metadata))
        with self._session() as session:
            existing = session.execute(
                select(GraphCheckpointRecord).where(
                    GraphCheckpointRecord.thread_id == record.thread_id,
                    GraphCheckpointRecord.checkpoint_ns == record.checkpoint_ns,
                    GraphCheckpointRecord.checkpoint_id == record.checkpoint_id,
                )
            ).scalars().first()
            if existing is None:
                session.add(record)
            else:
                existing.parent_checkpoint_id = record.parent_checkpoint_id
                existing.checkpoint = record.checkpoint
                existing.checkpoint_metadata = record.checkpoint_metadata
                existing.pending_writes = record.pending_writes
                existing.updated_at = record.updated_at
            session.commit()
        return {
            "configurable": {
                "thread_id": record.thread_id,
                "checkpoint_ns": record.checkpoint_ns,
                "checkpoint_id": record.checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        with self._session() as session:
            session.execute(
                delete(GraphCheckpointWriteRecord).where(
                    GraphCheckpointWriteRecord.thread_id == thread_id,
                    GraphCheckpointWriteRecord.checkpoint_ns == checkpoint_ns,
                    GraphCheckpointWriteRecord.checkpoint_id == checkpoint_id,
                    GraphCheckpointWriteRecord.task_id == task_id,
                )
            )
            for idx, (channel, value) in enumerate(writes):
                session.add(
                    GraphCheckpointWriteRecord(
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
            checkpoint_row = session.execute(
                select(GraphCheckpointRecord).where(
                    GraphCheckpointRecord.thread_id == thread_id,
                    GraphCheckpointRecord.checkpoint_ns == checkpoint_ns,
                    GraphCheckpointRecord.checkpoint_id == checkpoint_id,
                )
            ).scalars().first()
            if checkpoint_row is not None:
                checkpoint_row.pending_writes = [
                    self._pending_write_to_dict((task_id, channel, value))
                    for channel, value in writes
                ]
                checkpoint_row.updated_at = _now()
            session.commit()

    def delete_thread(self, thread_id: str) -> None:
        with self._session() as session:
            session.execute(
                delete(GraphCheckpointWriteRecord).where(GraphCheckpointWriteRecord.thread_id == thread_id)
            )
            session.execute(delete(GraphCheckpointRecord).where(GraphCheckpointRecord.thread_id == thread_id))
            session.commit()

    def delete_for_runs(self, run_ids):
        for run_id in run_ids:
            self.delete_thread(run_id)

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        with self._session() as session:
            checkpoint_rows = session.execute(
                select(GraphCheckpointRecord).where(GraphCheckpointRecord.thread_id == source_thread_id)
            ).scalars().all()
            write_rows = session.execute(
                select(GraphCheckpointWriteRecord).where(GraphCheckpointWriteRecord.thread_id == source_thread_id)
            ).scalars().all()
            for row in checkpoint_rows:
                session.add(
                    GraphCheckpointRecord(
                        thread_id=target_thread_id,
                        checkpoint_ns=row.checkpoint_ns,
                        checkpoint_id=row.checkpoint_id,
                        parent_checkpoint_id=row.parent_checkpoint_id,
                        checkpoint=row.checkpoint,
                        checkpoint_metadata=row.checkpoint_metadata,
                        pending_writes=row.pending_writes,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )
            for row in write_rows:
                session.add(
                    GraphCheckpointWriteRecord(
                        thread_id=target_thread_id,
                        checkpoint_ns=row.checkpoint_ns,
                        checkpoint_id=row.checkpoint_id,
                        task_id=row.task_id,
                        task_path=row.task_path,
                        write_idx=row.write_idx,
                        channel=row.channel,
                        value=row.value,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )
            session.commit()

    def prune(self, thread_ids, *, strategy: str = "keep_latest") -> None:
        if strategy == "delete":
            for thread_id in thread_ids:
                self.delete_thread(thread_id)
            return

        with self._session() as session:
            for thread_id in thread_ids:
                rows = session.execute(
                    select(GraphCheckpointRecord).where(GraphCheckpointRecord.thread_id == thread_id)
                ).scalars().all()
                by_ns: dict[str, list[GraphCheckpointRecord]] = {}
                for row in rows:
                    by_ns.setdefault(row.checkpoint_ns, []).append(row)
                for checkpoint_ns, ns_rows in by_ns.items():
                    if not ns_rows:
                        continue
                    latest = max(ns_rows, key=lambda row: row.id)
                    for row in ns_rows:
                        if row.id == latest.id:
                            continue
                        session.execute(
                            delete(GraphCheckpointWriteRecord).where(
                                GraphCheckpointWriteRecord.thread_id == thread_id,
                                GraphCheckpointWriteRecord.checkpoint_ns == checkpoint_ns,
                                GraphCheckpointWriteRecord.checkpoint_id == row.checkpoint_id,
                            )
                        )
                        session.delete(row)
            session.commit()

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    async def alist(self, config: RunnableConfig | None, *, filter: dict[str, Any] | None = None, before: RunnableConfig | None = None, limit: int | None = None):
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, Any],
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: list[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return self.put_writes(config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        return self.delete_thread(thread_id)

    async def adelete_for_runs(self, run_ids) -> None:
        return self.delete_for_runs(run_ids)

    async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        return self.copy_thread(source_thread_id, target_thread_id)

    async def aprune(self, thread_ids, *, strategy: str = "keep_latest") -> None:
        return self.prune(thread_ids, strategy=strategy)


@dataclass(frozen=True)
class MemoryCheckpointStore:
    def build(self):
        return MemorySaver().with_allowlist(ALLOWLISTED_CHECKPOINT_TYPES)


@dataclass(frozen=True)
class DatabaseCheckpointStore:
    def build(self):
        return DatabaseCheckpointSaver().with_allowlist(ALLOWLISTED_CHECKPOINT_TYPES)


@dataclass(frozen=True)
class NoCheckpointStore:
    def build(self):
        return None
