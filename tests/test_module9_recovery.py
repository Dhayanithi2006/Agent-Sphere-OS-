"""Unit and integration tests for Module 9 (Recovery Engine)."""

from __future__ import annotations

import asyncio
import pytest

from app.core.config import AppSettings
from app.dependency.dependency_manager import DependencyManager
from app.checkpoint.checkpoint_manager import CheckpointManager
from app.events.event_bus import EventBus
from app.runtime.recovery import RecoveryEngine
from app.events.event_types import EVENT_RECOVERY_COMPLETED, EVENT_ROLLBACK_TRIGGERED


@pytest.fixture
async def setup_recovery() -> tuple[RecoveryEngine, DependencyManager, CheckpointManager, EventBus]:
    """Fixture providing isolated recovery stack with local configs."""
    event_settings = AppSettings(event_log_path="test_rec_events.jsonl", dlq_log_path="test_rec_dlq.jsonl")
    bus = EventBus(event_settings)
    await bus.start()

    deps = DependencyManager()
    cps = CheckpointManager(db_path=":memory:")
    recovery = RecoveryEngine(dependency_manager=deps, checkpoint_manager=cps, event_bus=bus)
    
    return recovery, deps, cps, bus


@pytest.mark.anyio
async def test_topological_recovery_planning(setup_recovery):
    """Verify that affected downstream agents are planned in topological execution order."""
    recovery, deps, _, bus = setup_recovery

    # planner depends on researcher, researcher depends on developer, developer on reviewer
    # Note: add_dependency(source, target) -> source depends on target (target runs first)
    deps.add_dependency("reviewer", "tester")
    deps.add_dependency("tester", "developer")
    deps.add_dependency("developer", "researcher")

    # If developer fails, affected downstream nodes are: tester and reviewer
    # They should execute in order: tester -> reviewer
    plan = recovery.plan_recovery("developer")
    assert plan == ["tester", "reviewer"]

    await bus.stop()


@pytest.mark.anyio
async def test_state_rollback_integration(setup_recovery):
    """Verify that recovery rolls back all downstream agents to their latest checkpoints."""
    recovery, deps, cps, bus = setup_recovery

    # Structure: reviewer depends on developer
    deps.add_dependency("reviewer", "developer")

    # Save checkpoints for both developer and reviewer
    cps.save_checkpoint("developer", {"val": "dev_ok"})
    cps.save_checkpoint("reviewer", {"val": "rev_ok"})

    # Trigger failure of developer
    plan = recovery.recover("developer")

    assert plan == ["reviewer"]
    # Check that reviewer was rolled back (restored)
    assert recovery.metrics["restores"] == 1 # only reviewer rolled back
    assert recovery.metrics["recovery_count"] == 1
    assert recovery.metrics["rollbacks"] == 1

    await bus.stop()



@pytest.mark.anyio
async def test_recovery_event_broadcasting(setup_recovery):
    """Verify that recovery cycles publish RollbackTriggered and RecoveryCompleted events."""
    recovery, deps, cps, bus = setup_recovery

    events_captured = []
    bus.subscribe(EVENT_ROLLBACK_TRIGGERED, lambda p: events_captured.append(("triggered", p)))
    bus.subscribe(EVENT_RECOVERY_COMPLETED, lambda p: events_captured.append(("completed", p)))

    deps.add_dependency("reviewer", "developer")
    cps.save_checkpoint("developer", {"val": "dev_ok"})
    cps.save_checkpoint("reviewer", {"val": "rev_ok"})

    # Execute recovery
    recovery.recover("developer", payload={"error": "OOM Exception"})

    # Allow event bus loop to finish
    await asyncio.sleep(0.1)
    await bus.stop()

    # Clean up event files
    import os
    for path in ["test_rec_events.jsonl", "test_rec_dlq.jsonl"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # Verify notifications captured
    assert len(events_captured) == 2
    assert events_captured[0][0] == "triggered"
    assert events_captured[0][1]["failed_agent_id"] == "developer"
    assert events_captured[0][1]["payload"] == {"error": "OOM Exception"}
    
    assert events_captured[1][0] == "completed"
    assert events_captured[1][1]["failed_agent_id"] == "developer"
    assert "reviewer" in events_captured[1][1]["affected_agents"]
