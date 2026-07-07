"""Persistent, thread-safe shared memory for inter-agent data exchange."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any


class SharedMemory:
    """A shared memory namespace backed by SQLite and guarded by a lock."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.path.join(os.getcwd(), "shared_memory.sqlite")
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._ensure_parent_directory()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._db_path == ":memory:" and self._connection is not None:
            return self._connection
        connection = sqlite3.connect(self._db_path, check_same_thread=False, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
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
                    CREATE TABLE IF NOT EXISTS memory_items (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def set(self, key: str, value: Any) -> None:
        """Store a value in shared memory."""
        self.write(namespace=None, key=key, value=value)

    def update(self, key: str, value: Any) -> None:
        """Update an existing value in shared memory."""
        self.set(key, value)

    def write(self, namespace: str | None, key: str, value: Any) -> None:
        """Store a value in a namespace-aware memory entry."""
        with self._lock:
            serialized = self._serialize(value)
            now = self._now()
            storage_key = self._compose_key(namespace, key)
            connection = self._connect()
            try:
                connection.execute(
                    "INSERT INTO memory_items(key, value, updated_at) VALUES(?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                    (storage_key, serialized, now),
                )
                version = self._next_version(connection, storage_key)
                connection.execute(
                    "INSERT INTO memory_versions(key, value, version, created_at) VALUES(?, ?, ?, ?)",
                    (storage_key, serialized, version, now),
                )
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from shared memory."""
        return self.read(namespace=None, key=key, default=default)

    def read(self, namespace: str | None, key: str, default: Any = None) -> Any:
        """Retrieve a value from a namespace-aware memory entry."""
        with self._lock:
            storage_key = self._compose_key(namespace, key)
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT value FROM memory_items WHERE key = ?",
                    (storage_key,),
                ).fetchone()
                if row is None:
                    return default
                return self._deserialize(row["value"])
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def exists(self, key: str) -> bool:
        """Return whether a key exists in shared memory."""
        return self.get(key, _MISSING) is not _MISSING

    def delete(self, key: str) -> None:
        """Remove a value from shared memory."""
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("DELETE FROM memory_items WHERE key = ?", (key,))
                connection.execute("DELETE FROM memory_versions WHERE key = ?", (key,))
                connection.commit()
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def clear(self) -> None:
        """Clear all shared memory contents."""
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("DELETE FROM memory_items")
                connection.execute("DELETE FROM memory_versions")
                connection.commit()
            finally:
                connection.close()

    def keys(self) -> list[str]:
        """Return the current shared memory keys."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute("SELECT key FROM memory_items ORDER BY key").fetchall()
                return [row["key"] for row in rows]
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of the current memory contents."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute("SELECT key, value FROM memory_items ORDER BY key").fetchall()
                return {row["key"]: self._deserialize(row["value"]) for row in rows}
            finally:
                connection.close()

    def version_history(self, key: str) -> list[dict[str, Any]]:
        """Return the full version history for a key."""
        return self.history(namespace=None, key=key)

    def history(self, namespace: str | None, key: str) -> list[dict[str, Any]]:
        """Return the full version history for a namespace-aware key."""
        with self._lock:
            storage_key = self._compose_key(namespace, key)
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT value, version, created_at FROM memory_versions WHERE key = ? ORDER BY version ASC",
                    (storage_key,),
                ).fetchall()
                return [
                    {
                        "value": self._deserialize(row["value"]),
                        "version": row["version"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
            finally:
                if self._db_path != ":memory:":
                    connection.close()

    def _next_version(self, connection: sqlite3.Connection, key: str) -> int:
        latest = connection.execute(
            "SELECT MAX(version) AS version FROM memory_versions WHERE key = ?",
            (key,),
        ).fetchone()
        return 1 if latest is None or latest["version"] is None else int(latest["version"]) + 1

    @staticmethod
    def _compose_key(namespace: str | None, key: str) -> str:
        if namespace:
            return f"{namespace}:{key}"
        return key

    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _deserialize(value: str) -> Any:
        return json.loads(value)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


_MISSING = object()
