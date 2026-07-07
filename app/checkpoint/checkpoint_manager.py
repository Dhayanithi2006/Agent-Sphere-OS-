"""Checkpoint manager for restoring agent state after failures."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

from app.models.checkpoint import Checkpoint


class CheckpointManager:
    """Stores snapshots of agent or task state for recovery workflows."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.path.join(os.getcwd(), "checkpoints.sqlite")
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._ensure_parent_directory()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._db_path == ":memory:" and self._connection is not None:
            return self._connection
        connection = sqlite3.connect(self._db_path, check_same_thread=False, isolation_level=None)
        connection.row_factory = sqlite3.Row
        if self._db_path == ":memory:":
            self._connection = connection
        return connection

    def _ensure_parent_directory(self) -> None:
        parent = os.path.dirname(self._db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _ensure_schema(self) -> None:
        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        state TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def create_checkpoint(self, task_id: str, name: str, state: dict[str, Any]) -> Checkpoint:
        """Persist a checkpoint for a task."""
        with self._lock:
            checkpoint_id = self._build_checkpoint_id(task_id)
            serialized = json.dumps(state, sort_keys=True)
            now = self._now()
            connection = self._connect()
            try:
                connection.execute(
                    "INSERT INTO checkpoints(id, task_id, name, state, created_at) VALUES(?, ?, ?, ?, ?)",
                    (checkpoint_id, task_id, name, serialized, now),
                )
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()
            return Checkpoint(
                id=checkpoint_id,
                task_id=task_id,
                name=name,
                state=state,
                created_at=datetime.fromisoformat(now)
            )

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Retrieve a previously saved checkpoint."""
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT id, task_id, name, state, created_at FROM checkpoints WHERE id = ?",
                    (checkpoint_id,),
                ).fetchone()
                if row is None:
                    return None
                return Checkpoint(
                    id=row["id"],
                    task_id=row["task_id"],
                    name=row["name"],
                    state=json.loads(row["state"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT id, task_id, name, state, created_at FROM checkpoints ORDER BY created_at DESC"
                ).fetchall()
                return [
                    Checkpoint(
                        id=row["id"],
                        task_id=row["task_id"],
                        name=row["name"],
                        state=json.loads(row["state"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                    for row in rows
                ]
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def restore(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore state from a checkpoint."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint is None:
            raise KeyError(f"Checkpoint {checkpoint_id} was not found")
        return checkpoint.state

    def save_checkpoint(self, target_id: str, payload: dict[str, Any] | None = None, *, manual: bool = False) -> Checkpoint:
        """Backward compatibility method."""
        return self.create_checkpoint(
            task_id=target_id,
            name=f"Checkpoint for {target_id}",
            state=payload or {}
        )

    @staticmethod
    def _build_checkpoint_id(task_id: str) -> str:
        return f"cp-{task_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
