"""Unit and integration tests for Module 14 (Execution Engine)."""

from __future__ import annotations

import sys
import time
from typing import Any
import pytest
from app.agents.base_agent import BaseAgent
from app.runtime.execution_engine import ExecutionEngine


class LoggingMockAgent(BaseAgent):
    """Mock agent printing to stdout and stderr, and returning a result."""

    def __init__(self, agent_id: str = "logger_agent", delay: float = 0.0) -> None:
        super().__init__(agent_id=agent_id, name=agent_id)
        self.delay = delay

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        print(f"Stdout log from {self.agent_id}")
        sys.stderr.write(f"Stderr error log from {self.agent_id}\n")
        if self.delay > 0:
            time.sleep(self.delay)
        return f"Executed payload: {payload}"


def test_stdout_stderr_and_resource_metrics_capturing():
    """Verify stdout/stderr capture, duration timing, and memory tracing."""
    ee = ExecutionEngine()
    agent = LoggingMockAgent(agent_id="test_captures")

    # Run execution
    res = ee.execute_agent(agent, payload={"test": "data"})

    assert res.success is True
    assert res.output == "Executed payload: {'test': 'data'}"
    assert "Stdout log from test_captures" in res.stdout
    assert "Stderr error log from test_captures" in res.stderr
    assert res.duration_seconds > 0.0
    assert res.memory_used_mb >= 0.0

    # Check metrics and history recording
    metrics = ee.get_metrics()
    assert metrics["total_executions"] == 1
    assert metrics["success_count"] == 1

    history = ee.get_execution_history()
    assert len(history) == 1
    assert history[0]["agent_id"] == "test_captures"
    assert "Stdout log from test_captures" in history[0]["stdout"]
    assert "Stderr error log from test_captures" in history[0]["stderr"]
    assert history[0]["duration_seconds"] > 0.0


def test_parallel_execution_speed():
    """Verify that multiple agents execute concurrently in parallel."""
    ee = ExecutionEngine()
    # Three agents, each sleeping for 0.1s
    agents = [
        LoggingMockAgent("agent_1", delay=0.1),
        LoggingMockAgent("agent_2", delay=0.1),
        LoggingMockAgent("agent_3", delay=0.1),
    ]

    start = time.perf_counter()
    results = ee.execute_parallel(agents)
    elapsed = time.perf_counter() - start

    assert len(results) == 3
    assert all(r.success for r in results)
    # If sequential, it would take >= 0.3s. In parallel, it should take < 0.25s.
    assert elapsed < 0.25


def test_dynamic_concurrency_limiting():
    """Verify that dynamic concurrency limits restrict thread pool sizes correctly."""
    ee = ExecutionEngine()
    
    # Restrict concurrency to 2 threads
    ee.set_concurrency_limit(2)

    # 4 agents, each sleeping for 0.1s
    agents = [
        LoggingMockAgent("agent_a", delay=0.1),
        LoggingMockAgent("agent_b", delay=0.1),
        LoggingMockAgent("agent_c", delay=0.1),
        LoggingMockAgent("agent_d", delay=0.1),
    ]

    start = time.perf_counter()
    results = ee.execute_parallel(agents)
    elapsed = time.perf_counter() - start

    assert len(results) == 4
    # With max 2 workers, 4 tasks of 0.1s must run in 2 batches, taking >= 0.2s.
    assert elapsed >= 0.18
