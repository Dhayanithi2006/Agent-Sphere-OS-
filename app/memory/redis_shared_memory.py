"""Redis-backed shared memory implementation for AgentSphere OS."""

from __future__ import annotations

import json
from typing import Any

import redis

from app.core.logger import get_logger


class RedisSharedMemory:
    """Shared memory backed by Redis for fast state and version history."""

    def __init__(self, redis_url: str, namespace_prefix: str = "agentsphere") -> None:
        self.logger = get_logger("agentsphere.memory.redis_shared_memory")
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._namespace_prefix = namespace_prefix

    def _compose_key(self, namespace: str | None, key: str) -> str:
        prefix = f"{self._namespace_prefix}:" if self._namespace_prefix else ""
        if namespace:
            return f"{prefix}{namespace}:{key}"
        return f"{prefix}{key}"

    def _serialize(self, value: Any) -> str:
        return json.dumps(value, sort_keys=True)

    def _deserialize(self, value: str) -> Any:
        return json.loads(value)

    def set(self, key: str, value: Any) -> None:
        self.write(namespace=None, key=key, value=value)

    def update(self, key: str, value: Any) -> None:
        self.set(key, value)

    def write(self, namespace: str | None, key: str, value: Any) -> None:
        storage_key = self._compose_key(namespace, key)
        serialized = self._serialize(value)
        self._client.set(storage_key, serialized)
        self._client.rpush(f"{storage_key}:history", serialized)

    def get(self, key: str, default: Any = None) -> Any:
        return self.read(namespace=None, key=key, default=default)

    def read(self, namespace: str | None, key: str, default: Any = None) -> Any:
        storage_key = self._compose_key(namespace, key)
        value = self._client.get(storage_key)
        if value is None:
            return default
        return self._deserialize(value)

    def exists(self, key: str) -> bool:
        return self._client.exists(key) == 1

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def clear(self) -> None:
        keys = list(self._client.scan_iter(f"{self._namespace_prefix}:*"))
        if keys:
            self._client.delete(*keys)

    def keys(self) -> list[str]:
        return [key for key in self._client.scan_iter(f"{self._namespace_prefix}:*")]

    def snapshot(self) -> dict[str, Any]:
        snapshot = {}
        for key in self.keys():
            if key.endswith(":history"):
                continue
            raw = self._client.get(key)
            if raw is None:
                continue
            snapshot[key] = self._deserialize(raw)
        return snapshot

    def history(self, namespace: str | None, key: str) -> list[dict[str, Any]]:
        storage_key = self._compose_key(namespace, key)
        raw_history = self._client.lrange(f"{storage_key}:history", 0, -1)
        return [{"value": self._deserialize(entry), "index": index} for index, entry in enumerate(raw_history)]

    def version_history(self, key: str) -> list[dict[str, Any]]:
        return self.history(namespace=None, key=key)
