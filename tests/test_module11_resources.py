"""Unit and integration tests for Module 11 (Resource Manager)."""

from __future__ import annotations

import asyncio
import pytest
from app.core.config import AppSettings
from app.events.event_bus import EventBus
from app.runtime.process_repository import InMemoryProcessRepository
from app.runtime.process_manager import ProcessManager
from app.resources.resource_manager import ResourceManager, EVENT_RESOURCE_LIMIT_EXCEEDED
from app.models.process import ProcessStatus


@pytest.fixture
async def setup_resource_test() -> tuple[ResourceManager, ProcessManager, EventBus]:
    """Fixture providing isolated resource manager, process manager and event bus."""
    event_settings = AppSettings(event_log_path="test_res_events.jsonl", dlq_log_path="test_res_dlq.jsonl")
    bus = EventBus(event_settings)
    await bus.start()

    repo = InMemoryProcessRepository()
    pm = ProcessManager(repo)
    rm = ResourceManager(process_manager=pm, event_bus=bus)

    return rm, pm, bus


@pytest.mark.anyio
async def test_system_metrics_structure(setup_resource_test):
    """Verify that system metrics format matches standard fields (CPU, memory, disk)."""
    rm, _, bus = setup_resource_test
    metrics = rm.get_system_metrics()

    assert "cpu_percent" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    assert "percent" in metrics["memory"]
    assert "percent" in metrics["disk"]

    await bus.stop()



@pytest.mark.anyio
async def test_resource_limits_monitoring_and_suspend(setup_resource_test):
    """Verify process limits monitoring, automatic suspension, and event notifications."""
    rm, pm, bus = setup_resource_test

    # 1. Create and start a simulated running process
    proc = await pm.create_process("agent_worker_1")
    await pm.start_process(proc.process_id)

    # Subscribe to resource warning events
    events_captured = []
    bus.subscribe(EVENT_RESOURCE_LIMIT_EXCEEDED, lambda payload: events_captured.append(payload))

    # 2. Register process with resource boundaries
    rm.register_process(proc.process_id, cpu_limit=70.0, memory_limit_mb=256.0)

    # 3. Simulate usage below limits and check
    rm.set_virtual_usage(proc.process_id, cpu=45.0, memory_mb=100.0)
    suspended_pids = await rm.check_limits()
    assert not suspended_pids

    # Confirm process remains running
    current_proc = await pm.repository.get(proc.process_id)
    assert current_proc.status == ProcessStatus.RUNNING

    # 4. Simulate usage exceeding limits and check
    rm.set_virtual_usage(proc.process_id, cpu=85.0, memory_mb=100.0)
    suspended_pids = await rm.check_limits()

    # Confirm process got suspended and alert was generated
    assert suspended_pids == [proc.process_id]
    current_proc = await pm.repository.get(proc.process_id)
    assert current_proc.status == ProcessStatus.SUSPENDED

    # Allow event loop dispatch
    await asyncio.sleep(0.05)
    await bus.stop()

    # Clean up files
    import os
    for path in ["test_res_events.jsonl", "test_res_dlq.jsonl"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # Verify event bus alert
    assert len(events_captured) == 1
    assert events_captured[0]["pid"] == proc.process_id
    assert events_captured[0]["cpu_percent"] == 85.0
