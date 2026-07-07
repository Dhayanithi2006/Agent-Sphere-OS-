"""Simple scheduler for agent execution tasks."""

from __future__ import annotations

from collections import deque
from typing import Deque, TypeVar

T = TypeVar("T")


class Scheduler:
    """A scheduler for work items with priority, FIFO, pause/resume, and concurrency support."""

    def __init__(self) -> None:
        self._queue: Deque[tuple[int, T]] = deque()
        self._paused: set[T] = set()
        self._active: set[T] = set()

    def enqueue(self, item: T, *, priority: int = 0) -> None:
        """Add an item to the scheduler queue."""
        self._queue.append((priority, item))
        self._queue = deque(sorted(self._queue, key=lambda entry: (entry[0], entry[1])))

    def dequeue(self) -> T:
        """Remove and return the next queued item."""
        if not self._queue:
            raise IndexError("Scheduler queue is empty")
        _, item = self._queue.popleft()
        self._active.add(item)
        return item

    def pause(self, item: T) -> None:
        """Pause a queued or active item."""
        self._paused.add(item)

    def resume(self, item: T) -> None:
        """Resume a paused item."""
        self._paused.discard(item)

    def is_paused(self, item: T) -> bool:
        """Return whether an item is currently paused."""
        return item in self._paused

    def size(self) -> int:
        """Return the number of queued items."""
        return len(self._queue)

    def active_count(self) -> int:
        """Return the number of currently active items."""
        return len(self._active)

    def queue_snapshot(self) -> list[T]:
        """Return the current queue contents."""
        return [item for _, item in self._queue]
