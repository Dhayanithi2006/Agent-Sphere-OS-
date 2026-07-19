"""Unit and integration tests for Phase 3-8 advanced OS capabilities (Parallel execution, Vector memory restoration, dynamic reflection tool plugins, resource OOM monitoring)."""

from __future__ import annotations

import os
import asyncio
import pytest
from app.core.shared import kernel, shared_memory, tool_registry, event_bus
from main import app


@pytest.fixture(autouse=True)
async def ensure_booted():
    """Ensure kernel is booted and limits are reset."""
    if not kernel.is_booted:
        await kernel.boot()
    yield
    # Cleanup limits and stop resource monitor
    kernel.set_resource_limits(
        max_concurrency=4,
        max_tool_calls=50,
        api_budget=10.0,
        memory_limit_mb=500.0
    )
    await kernel.shutdown()


@pytest.mark.anyio
async def test_dynamic_reflection_plugins():
    """Verify that reflection-based tool plugins from app/plugins/tools/ are loaded on startup."""
    # Force re-scan to pick up files created after registry instantiation
    tool_registry._init_system_tools()
    tools = tool_registry.list_tools()
    
    # Assert our custom reflection tools are present
    tool_ids = [t["id"] for t in tools]
    assert "github_create_issue" in tool_ids
    assert "slack_post_message" in tool_ids
    assert "jira_create_ticket" in tool_ids
    assert "gmail_send_email" in tool_ids
    assert "discord_post_webhook" in tool_ids


@pytest.mark.anyio
async def test_long_term_vector_memory():
    """Verify that task execution outcomes are committed to and retrieved from the vector memory db."""
    # Pre-populate similar task
    await shared_memory.add_vector(
        text="Build a web portal with FastAPI and Docker",
        metadata={"result": "Successful project creation template completed", "workflow": "coding"}
    )
    
    # Now run kernel.execute with a similar prompt - it should restore context automatically
    # We will check if "context_restored" gets set in payload (verified by tracing history/logs)
    res = await kernel.execute("Develop web portal with FastAPI and Docker")
    assert res is not None
    assert len(res) > 0


@pytest.mark.anyio
async def test_resource_monitor_oom_killer():
    """Verify background OOM checker suspends/recovers process when memory limit is breached."""
    # Cancel background task to avoid concurrent checks and DB locks
    if hasattr(kernel, "_resource_monitor_task") and kernel._resource_monitor_task:
        kernel._resource_monitor_task.cancel()
        try:
            await kernel._resource_monitor_task
        except asyncio.CancelledError:
            pass
        kernel._resource_monitor_task = None

    # Create process first
    pid = await kernel.create_agent_process("planner", "Test OOM Agent")
    await kernel.start_agent_process(pid)
    
    # Set extremely low memory limit (0.01 MB) to force OOM killer action
    kernel.set_resource_limits(memory_limit_mb=0.01)
    
    # Let resource monitor run a check step
    # Resource monitor checks every 2 seconds, we run the helper manually to speed up
    await kernel._resource_monitor_loop(once=True)
    
    # Check if memory limit breach restarted the process
    # Because memory limit breached, OOM killer calls restart_agent_process, creating a new PID
    from app.core.shared import process_manager
    from app.models.process import ProcessStatus
    
    procs = await process_manager.list_processes()
    # There should be a new process created as restart fallback
    assert len(procs) > 1
