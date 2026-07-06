"""Shared in-memory store for inter-agent data exchange."""

from __future__ import annotations

from typing import Any


class SharedMemory:
    """A simple shared memory namespace for passing data between agents."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Store a value in shared memory."""
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from shared memory."""
        return self._store.get(key, default)

    def exists(self, key: str) -> bool:
        """Return whether a key exists in shared memory."""
        return key in self._store

    def delete(self, key: str) -> None:
        """Remove a value from shared memory."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all shared memory contents."""
        self._store.clear()

    def keys(self) -> list[str]:
        """Return the current shared memory keys."""
        return list(self._store.keys())
