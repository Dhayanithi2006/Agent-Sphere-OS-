"""Memory manager that selects the best storage backend for shared state."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.memory.redis_shared_memory import RedisSharedMemory
from app.memory.shared_memory import SharedMemory


class MemoryManager:
    """Factory for shared memory backends."""

    def __init__(self) -> None:
        if settings.redis_url:
            self.backend = RedisSharedMemory(settings.redis_url)
        else:
            self.backend = SharedMemory()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.backend, name)

    @property
    def backend_type(self) -> str:
        return "redis" if settings.redis_url else "sqlite"
