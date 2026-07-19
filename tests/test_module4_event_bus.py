"""Unit and integration tests for Module 4 (Asynchronous Event Bus)."""

from __future__ import annotations

import asyncio
import os
import pytest
from datetime import datetime, timezone

from app.core.config import AppSettings
from app.events.event_bus import EventBus
from app.events.event_models import EventPriority


@pytest.fixture
def clean_test_settings(tmp_path) -> AppSettings:
    """Fixture providing isolated temporary log paths for tests."""
    event_file = tmp_path / "test_events.jsonl"
    dlq_file = tmp_path / "test_dlq.jsonl"
    return AppSettings(
        event_log_path=str(event_file),
        dlq_log_path=str(dlq_file)
    )


def test_sync_fallback_publish_and_subscribe(clean_test_settings):
    """Verify that when no event loop is running, the event bus falls back to sync dispatch."""
    bus = EventBus(clean_test_settings)
    events_received = []

    bus.subscribe("agent_log", lambda p: events_received.append(p))
    bus.publish("agent_log", "sync payload")

    assert events_received == ["sync payload"]
    # Check that it persisted synchronously
    assert os.path.exists(clean_test_settings.event_log_path)


@pytest.mark.anyio
async def test_async_priority_dispatching(clean_test_settings):
    """Verify high priority events are popped and handled before lower priority ones."""
    bus = EventBus(clean_test_settings)
    handled_payloads = []

    # Subscribe to test event type
    bus.subscribe("compute_task", lambda p: handled_payloads.append(p))

    # Publish events to queue while dispatch loop is not started yet (queue buffer phase)
    bus.publish("compute_task", payload="low_work", priority=EventPriority.LOW)
    bus.publish("compute_task", payload="high_work", priority=EventPriority.HIGH)
    bus.publish("compute_task", payload="medium_work", priority=EventPriority.MEDIUM)

    # Start dispatch processing loop
    await bus.start()
    
    # Wait briefly for priority queue to flush through event loop
    await asyncio.sleep(0.2)
    await bus.stop()

    # High priority must be first, then medium, then low
    assert handled_payloads == ["high_work", "medium_work", "low_work"]


@pytest.mark.anyio
async def test_dead_letter_queue_persistence(clean_test_settings):
    """Verify failing subscriber handlers cause events to route to DLQ log file."""
    bus = EventBus(clean_test_settings)

    def failing_handler(payload):
        raise ValueError("Subscriber failed purposefully")

    bus.subscribe("dangerous_event", failing_handler)
    
    await bus.start()
    bus.publish("dangerous_event", "crash data")
    
    await asyncio.sleep(0.2)
    await bus.stop()

    # The event should be written to the DLQ log path
    assert os.path.exists(clean_test_settings.dlq_log_path)
    with open(clean_test_settings.dlq_log_path, "r", encoding="utf-8") as f:
        dlq_lines = f.readlines()
    
    assert len(dlq_lines) == 1
    assert "Subscriber failed purposefully" in dlq_lines[0]
    assert "dangerous_event" in dlq_lines[0]


@pytest.mark.anyio
async def test_event_replay_mechanism(clean_test_settings):
    """Verify replaying past events from file log, filtering by time and type."""
    bus = EventBus(clean_test_settings)

    # Publish events to persist them
    bus.publish("agent_log", "msg1")
    bus.publish("system_log", "msg2")
    bus.publish("agent_log", "msg3")

    # Replay all
    all_events = await bus.replay()
    assert len(all_events) == 3

    # Replay filtered by type
    agent_events = await bus.replay(event_type="agent_log")
    assert len(agent_events) == 2
    assert agent_events[0].payload == "msg1"
    assert agent_events[1].payload == "msg3"

    # Test replay with dispatching triggered
    replayed_payloads = []
    bus.subscribe("agent_log", lambda p: replayed_payloads.append(p))

    # Replay and dispatch
    await bus.replay(event_type="agent_log", dispatch=True)
    assert replayed_payloads == ["msg1", "msg3"]
