"""Backwards-compatible SharedMemory adapter delegating to MemoryManager."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from app.memory.memory_manager import MemoryManager


class SharedMemory(MemoryManager):
    """Wrapper class preserving legacy SharedMemory interface signatures on top of MemoryManager."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__(db_path=db_path)

    def set(self, key: str, value: Any) -> None:
        """Store value in memory (legacy interface)."""
        self.write(namespace=None, key=key, value=value)

    def update(self, key: str, value: Any) -> None:
        """Update value in memory (legacy interface)."""
        self.set(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from memory (legacy interface)."""
        return self.read(namespace=None, key=key, default=default)

    def exists(self, key: str) -> bool:
        """Check if key exists in memory (legacy interface)."""
        return super().exists(namespace=None, key=key)

    def delete(self, key: str) -> None:
        """Delete key and versions (legacy interface)."""
        super().delete(namespace=None, key=key)

    def clear(self) -> None:
        """Clear database tables."""
        connection = self._connect()
        try:
            connection.execute("DELETE FROM memory_items")
            connection.execute("DELETE FROM memory_versions")
            connection.execute("DELETE FROM vector_items")
            connection.commit()
        finally:
            connection.close()

    def keys(self) -> List[str]:
        """Fetch all keys (legacy interface)."""
        connection = self._connect()
        try:
            rows = connection.execute("SELECT key FROM memory_items ORDER BY key").fetchall()
            return [row["key"] for row in rows]
        finally:
            connection.close()

    def snapshot(self) -> Dict[str, Any]:
        """Dump active database key-value state (legacy interface)."""
        connection = self._connect()
        try:
            rows = connection.execute("SELECT key, value FROM memory_items ORDER BY key").fetchall()
            return {row["key"]: json.loads(row["value"]) for row in rows}
        finally:
            connection.close()

    def version_history(self, key: str) -> List[Dict[str, Any]]:
        """Fetch version list of updates to a key (legacy interface)."""
        return self.history(namespace=None, key=key)
