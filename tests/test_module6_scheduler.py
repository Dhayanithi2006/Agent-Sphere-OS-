"""Unit and integration tests for Module 6 (Asynchronous Scheduler)."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime

from app.runtime.scheduler import Scheduler
from app.events.event_bus import EventBus
from app.core.config import AppSettings


@pytest.fixture
def clean_scheduler() -> Scheduler:
    """Fixture providing a fresh isolated Scheduler instance."""
    return Scheduler(max_concurrency=2)


def test_legacy_sync_priority_queueing(clean_scheduler):
    """Verify that sync enqueue/dequeue sorts by priority and skips paused items."""
    scheduler = clean_scheduler
    
    # Priority sorting check (lower values executed first)
    scheduler.enqueue("task_low", priority=10)
    scheduler.enqueue("task_high_1", priority=1)
    scheduler.enqueue("task_high_2", priority=1)

    # Pop elements
    # Since task_high_1 and task_high_2 have the same priority, stable sort ensures FIFO
    assert scheduler.dequeue() == "task_high_1"
    assert scheduler.dequeue() == "task_high_2"
    assert scheduler.dequeue() == "task_low"

    # Pause / Resume check
    scheduler.enqueue("task_a", priority=1)
    scheduler.pause("task_a")
    assert scheduler.is_paused("task_a") is True

    scheduler.resume("task_a")
    assert scheduler.is_paused("task_a") is False


@pytest.mark.anyio
async def test_async_priority_execution(clean_scheduler):
    """Verify that tasks schedule and run based on priority levels when scheduler resumes."""
    scheduler = clean_scheduler
    scheduler.max_concurrency = 1
    scheduler.pause_scheduler() # Pause globally to stack items

    run_order = []

    async def worker_1():
        run_order.append("worker_low")

    async def worker_2():
        run_order.append("worker_high")

    async def worker_3():
        run_order.append("worker_med")

    # Schedule tasks asynchronously
    task1 = asyncio.create_task(scheduler.execute_task("task_low", worker_1, priority=3))
    task2 = asyncio.create_task(scheduler.execute_task("task_high", worker_2, priority=1))
    task3 = asyncio.create_task(scheduler.execute_task("task_med", worker_3, priority=2))

    await asyncio.sleep(0.1) # Let tasks register in queue
    assert scheduler.size() == 3

    scheduler.resume_scheduler() # Let them run

    # Wait for all to finish
    await asyncio.gather(task1, task2, task3)

    # Assert priority sorting (high, then med, then low)
    assert run_order == ["worker_high", "worker_med", "worker_low"]


@pytest.mark.anyio
async def test_scheduler_concurrency_throttle():
    """Verify that concurrency is limited to max_concurrency."""
    # Max concurrency set to 2
    scheduler = Scheduler(max_concurrency=2)
    active_peaks = []
    
    async def sleeping_worker(name):
        active_peaks.append(scheduler.active_count())
        await asyncio.sleep(0.1)

    # Schedule 4 parallel tasks
    tasks = [
        asyncio.create_task(scheduler.execute_task(f"t{i}", lambda i=i: sleeping_worker(f"t{i}")))
        for i in range(4)
    ]

    await asyncio.gather(*tasks)

    # Max active at any one time must never exceed 2
    assert all(peak <= 2 for peak in active_peaks)



@pytest.mark.anyio
async def test_scheduler_pause_gates(clean_scheduler):
    """Verify item-level and global pause states prevent tasks from executing."""
    scheduler = clean_scheduler
    execution_flag = False

    async def worker():
        nonlocal execution_flag
        execution_flag = True

    # 1. Global Scheduler Pause
    scheduler.pause_scheduler()
    task = asyncio.create_task(scheduler.execute_task("task_1", worker))
    await asyncio.sleep(0.1)
    
    assert execution_flag is False # Stalled
    assert scheduler.size() == 1

    scheduler.resume_scheduler()
    await task
    assert execution_flag is True # Ran successfully

    # 2. Item Pause
    execution_flag = False
    scheduler.pause("task_2")
    task2 = asyncio.create_task(scheduler.execute_task("task_2", worker))
    await asyncio.sleep(0.1)

    assert execution_flag is False # Stalled
    scheduler.resume("task_2")
    await task2
    assert execution_flag is True # Ran successfully


@pytest.mark.anyio
async def test_scheduler_event_broadcasts():
    """Verify scheduler actions publish structured events onto the shared EventBus."""
    from app.events.event_bus import EventBus
    
    # Create isolated EventBus specifically for this test
    bus = EventBus(AppSettings(event_log_path="test_sch_events.jsonl", dlq_log_path="test_sch_dlq.jsonl"))
    await bus.start()
    
    events_captured = []
    bus.subscribe("scheduler.task_enqueued", lambda p: events_captured.append(("enqueued", p)))
    bus.subscribe("scheduler.task_started", lambda p: events_captured.append(("started", p)))
    bus.subscribe("scheduler.task_completed", lambda p: events_captured.append(("completed", p)))

    # Inject the isolated EventBus instance
    scheduler = Scheduler(max_concurrency=2, event_bus=bus)
    assert scheduler._get_event_bus() == bus

    async def simple_job():
        pass

    await scheduler.execute_task("metric_job", simple_job, priority=5)

    # Allow event loop time to process the event bus queues
    await asyncio.sleep(0.1)
    await bus.stop()

    # Clean up test files
    import os
    for path in ["test_sch_events.jsonl", "test_sch_dlq.jsonl"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    assert len(events_captured) >= 3
    # Check sequences
    assert events_captured[0][0] == "enqueued"
    assert events_captured[0][1]["item"] == "metric_job"
    assert events_captured[1][0] == "started"
    assert events_captured[2][0] == "completed"
    assert events_captured[2][1]["success"] is True
