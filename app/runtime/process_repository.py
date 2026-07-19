"""Repository pattern implementations for managing process model records."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from app.models.process import Process


class ProcessRepository(ABC):
    """Interface declaring standard CRUD operations on Process data models."""

    @abstractmethod
    async def add(self, process: Process) -> None:
        """Persist a new process record."""

    @abstractmethod
    async def get(self, process_id: str) -> Optional[Process]:
        """Fetch a single process record by its process ID."""

    @abstractmethod
    async def update(self, process: Process) -> None:
        """Modify an existing process record."""

    @abstractmethod
    async def list(self) -> List[Process]:
        """Fetch all processes in the data store."""

    @abstractmethod
    async def delete(self, process_id: str) -> bool:
        """Remove a process record by its ID."""


class InMemoryProcessRepository(ProcessRepository):
    """Thread-safe, asynchronous in-memory implementation of ProcessRepository."""

    def __init__(self) -> None:
        self._store: Dict[str, Process] = {}
        self._lock = asyncio.Lock()

    async def add(self, process: Process) -> None:
        async with self._lock:
            self._store[process.process_id] = process

    async def get(self, process_id: str) -> Optional[Process]:
        async with self._lock:
            return self._store.get(process_id)

    async def update(self, process: Process) -> None:
        async with self._lock:
            self._store[process.process_id] = process

    async def list(self) -> List[Process]:
        async with self._lock:
            return list(self._store.values())

    async def delete(self, process_id: str) -> bool:
        async with self._lock:
            if process_id in self._store:
                del self._store[process_id]
                return True
            return False
