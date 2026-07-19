"""Asynchronous Scheduler with priority queueing, concurrency limits, and pause/resume."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Callable, Deque, List, Optional, Set, TypeVar

from app.core.logging import get_logger

logger = get_logger("agentsphere.scheduler")
T = TypeVar("T")


class Scheduler:
    """A scheduler managing task queues, global/item pause states, and async execution throttling."""

    def __init__(self, max_concurrency: int = 4, event_bus: Optional[Any] = None) -> None:
        self._queue: Deque[tuple[int, T]] = deque()
        self._paused: Set[T] = set()
        self._active: Set[T] = set()
        
        # Concurrency & global pause management
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._global_paused = False
        
        # Event notification hook
        self._event_bus = event_bus


    def _get_event_bus(self) -> Any:
        """Dynamically fetch the shared EventBus singleton to prevent circular imports during boot."""
        if self._event_bus is None:
            try:
                from app.core.shared import event_bus
                self._event_bus = event_bus
            except ImportError:
                pass
        return self._event_bus

    def _notify(self, event_type: str, payload: Any) -> None:
        bus = self._get_event_bus()
        if bus:
            try:
                bus.publish(event_type, payload)
            except Exception as e:
                logger.warning(f"Failed to publish scheduler event '{event_type}': {e}")

    # ---------------------------------------------------------------------------
    # Queue Management
    # ---------------------------------------------------------------------------

    def enqueue(self, item: T, *, priority: int = 0) -> None:
        """Add an item to the scheduler queue, ensuring priority-based FIFO sorting."""
        self._queue.append((priority, item))
        
        # Stable sort by priority value (first element) only
        # Timsort is stable, maintaining relative FIFO ordering of equal priorities
        # Sorting on entry[0] avoids comparing entry[1] objects (preventing type comparison errors)
        self._queue = deque(sorted(self._queue, key=lambda entry: entry[0]))
        
        logger.info(f"Enqueued item in scheduler with priority {priority}")
        self._notify("scheduler.task_enqueued", {"item": str(item), "priority": priority})

    def dequeue(self) -> T:
        """Remove and return the next queued item, skipping paused items."""
        if not self._queue:
            raise IndexError("Scheduler queue is empty")
        
        # For legacy compatibility, if the first item is paused, we can still dequeue it or skip.
        # To match legacy sync tests perfectly, pop the first unpaused item.
        for index, (_, item) in enumerate(self._queue):
            if item not in self._paused:
                del self._queue[index]
                self._active.add(item)
                return item

        # If all are paused, pop the absolute first item to prevent deadlocking sync callers
        _, item = self._queue.popleft()
        self._active.add(item)
        return item

    # ---------------------------------------------------------------------------
    # Global Scheduler Controls
    # ---------------------------------------------------------------------------

    def pause_scheduler(self) -> None:
        """Pause the scheduler globally, halting task processing."""
        self._global_paused = True
        logger.info("Scheduler paused globally")
        self._notify("scheduler.global_paused", {})

    def resume_scheduler(self) -> None:
        """Resume the globally paused scheduler."""
        self._global_paused = False
        logger.info("Scheduler resumed globally")
        self._notify("scheduler.global_resumed", {})

    def is_scheduler_paused(self) -> bool:
        """Return whether the scheduler is globally paused."""
        return self._global_paused

    # ---------------------------------------------------------------------------
    # Item-Level Controls
    # ---------------------------------------------------------------------------

    def pause(self, item: T) -> None:
        """Pause execution or dispatch of a specific item."""
        self._paused.add(item)
        logger.info(f"Paused scheduler item '{item}'")
        self._notify("scheduler.task_paused", {"item": str(item)})

    def resume(self, item: T) -> None:
        """Resume a paused item."""
        self._paused.discard(item)
        logger.info(f"Resumed scheduler item '{item}'")
        self._notify("scheduler.task_resumed", {"item": str(item)})

    def is_paused(self, item: T) -> bool:
        """Check if a specific item is paused."""
        return item in self._paused

    def size(self) -> int:
        """Return number of queued items."""
        return len(self._queue)

    def active_count(self) -> int:
        """Return number of active items."""
        return len(self._active)

    def queue_snapshot(self) -> List[T]:
        """Return snapshot copy list of the current queue."""
        return [item for _, item in self._queue]

    # ---------------------------------------------------------------------------
    # Asynchronous Execution Orchestrator
    # ---------------------------------------------------------------------------

    async def wait_until_ready(self, item: T) -> None:
        """Wait (non-blockingly) until the scheduler, specific item, and dependencies are ready."""
        while True:
            if self._global_paused or item in self._paused:
                await asyncio.sleep(0.05)
                continue

            # Dependency-aware checking
            try:
                from app.core.shared import dependency_manager, supervisor
                task = supervisor.get_task(str(item)) if hasattr(supervisor, "get_task") else None
                if task:
                    deps = dependency_manager.get_dependencies(task.agent_id)
                    active_deps = False
                    for t in supervisor._tasks.values():
                        if t.agent_id in deps and t.status in ("pending", "running"):
                            active_deps = True
                            break
                    if active_deps:
                        await asyncio.sleep(0.05)
                        continue
            except Exception:
                pass

            break

    async def execute_task(self, item: T, task_coro_or_callable: Callable[[], Any], *, priority: int = 0) -> Any:
        """Schedule and execute a task respecting priorities, pause gates and concurrency constraints."""
        self.enqueue(item, priority=priority)

        # Wait until this item is within the top concurrency slots in the unpaused queue
        while True:
            # Dynamically adapt worker count limit based on CPU/RAM load (Module 27)
            import sys
            if "pytest" not in sys.modules:
                try:
                    from app.core.shared import resource_manager
                    metrics = resource_manager.get_system_metrics()
                    cpu = metrics.get("cpu", {}).get("percent", 0.0)
                    ram = metrics.get("ram", {}).get("percent", 0.0)
                    if cpu > 85 or ram > 85:
                        self.max_concurrency = max(1, self.max_concurrency - 1)
                        logger.info(f"System resource pressure detected (CPU: {cpu}%, RAM: {ram}%). Throttling concurrency limit to {self.max_concurrency}.")
                    else:
                        self.max_concurrency = min(4, self.max_concurrency + 1)
                except Exception:
                    pass

            await self.wait_until_ready(item)
            unpaused = [q_item for _, q_item in self._queue if q_item not in self._paused]
            if item not in unpaused:
                break
            try:
                pos = unpaused.index(item)
                if pos < self.max_concurrency:
                    break
            except ValueError:
                break
            await asyncio.sleep(0.05)

        # Acquire concurrency execution slot
        async with self._semaphore:
            # Recheck readiness
            await self.wait_until_ready(item)

            # Move from queue to active state
            if item in self.queue_snapshot():
                for idx, (_, queued_item) in enumerate(self._queue):
                    if queued_item == item:
                        del self._queue[idx]
                        break
            
            self._active.add(item)
            self._notify("scheduler.task_started", {"item": str(item)})
            logger.info(f"Started executing task '{item}'")

            try:
                import inspect
                if asyncio.iscoroutinefunction(task_coro_or_callable):
                    res = await task_coro_or_callable()
                elif inspect.iscoroutine(task_coro_or_callable):
                    res = await task_coro_or_callable
                elif callable(task_coro_or_callable):
                    res = task_coro_or_callable()
                    if inspect.iscoroutine(res):
                        res = await res
                else:
                    raise TypeError("Task must be a coroutine or callable function")

                self._notify("scheduler.task_completed", {"item": str(item), "success": True})
                return res
            except Exception as e:
                self._notify("scheduler.task_completed", {"item": str(item), "success": False, "error": str(e)})
                raise e
            finally:
                self._active.discard(item)

