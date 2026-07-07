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
                        checkpoint_id TEXT PRIMARY KEY,
                        target_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def save_checkpoint(self, target_id: str, payload: dict[str, Any] | None = None, *, manual: bool = False) -> Checkpoint:
        """Persist a checkpoint for a target identifier."""
        with self._lock:
            checkpoint_id = self._build_checkpoint_id(target_id)
            version = self._next_version(target_id)
            serialized = json.dumps(payload or {}, sort_keys=True)
            now = self._now()
            connection = self._connect()
            try:
                connection.execute(
                    "INSERT INTO checkpoints(checkpoint_id, target_id, payload, version, created_at) VALUES(?, ?, ?, ?, ?)",
                    (checkpoint_id, target_id, serialized, version, now),
                )
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()
            return Checkpoint(checkpoint_id=checkpoint_id, target_id=target_id, payload=payload or {}, created_at=datetime.fromisoformat(now))

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Retrieve a previously saved checkpoint."""
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT checkpoint_id, target_id, payload, version, created_at FROM checkpoints WHERE checkpoint_id = ?",
                    (checkpoint_id,),
                ).fetchone()
                if row is None:
                    return None
                return Checkpoint(
                    checkpoint_id=row["checkpoint_id"],
                    target_id=row["target_id"],
                    payload=json.loads(row["payload"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def restore(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore payload from a checkpoint."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint is None:
            raise KeyError(f"Checkpoint {checkpoint_id} was not found")
        return checkpoint.payload

    def get_versions(self, target_id: str) -> list[str]:
        """Return the full checkpoint history for a target."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT checkpoint_id FROM checkpoints WHERE target_id = ? ORDER BY version ASC",
                    (target_id,),
                ).fetchall()
                return [row["checkpoint_id"] for row in rows]
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def get_latest(self, target_id: str) -> Checkpoint | None:
        """Return the latest checkpoint for a target."""
        versions = self.get_versions(target_id)
        if not versions:
            return None
        return self.get_checkpoint(versions[-1])

    def cleanup_old(self, keep_latest: int = 3) -> int:
        """Remove older checkpoints while preserving the latest versions per target."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT checkpoint_id, target_id FROM checkpoints ORDER BY created_at ASC"
                ).fetchall()
                by_target: dict[str, list[str]] = {}
                for row in rows:
                    by_target.setdefault(row["target_id"], []).append(row["checkpoint_id"])
                to_delete: list[str] = []
                for target_id, checkpoint_ids in by_target.items():
                    if len(checkpoint_ids) <= keep_latest:
                        continue
                    to_delete.extend(checkpoint_ids[:-keep_latest])
                if to_delete:
                    placeholders = ",".join("?" for _ in to_delete)
                    connection.execute(f"DELETE FROM checkpoints WHERE checkpoint_id IN ({placeholders})", to_delete)
                    connection.commit()
                return len(to_delete)
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def _next_version(self, target_id: str) -> int:
        connection = self._connect()
        try:
            latest = connection.execute(
                "SELECT MAX(version) AS version FROM checkpoints WHERE target_id = ?",
                (target_id,),
            ).fetchone()
            return 1 if latest is None or latest["version"] is None else int(latest["version"]) + 1
        finally:
            if self._db_path != ":memory:":
                connection.close()

    @staticmethod
    def _build_checkpoint_id(target_id: str) -> str:
        return f"cp-{target_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
