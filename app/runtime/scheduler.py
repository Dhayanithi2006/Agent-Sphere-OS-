"""Simple scheduler for agent execution tasks."""

from __future__ import annotations

from collections import deque
from typing import Callable, Deque, TypeVar

T = TypeVar("T")


class Scheduler:
    """A minimal FIFO scheduler for work items."""

    def __init__(self) -> None:
        self._queue: Deque[T] = deque()

    def enqueue(self, item: T) -> None:
        """Add an item to the scheduler queue."""
        self._queue.append(item)

    def dequeue(self) -> T:
        """Remove and return the next queued item."""
        if not self._queue:
            raise IndexError("Scheduler queue is empty")
        return self._queue.popleft()

    def size(self) -> int:
        """Return the number of queued items."""
        return len(self._queue)
