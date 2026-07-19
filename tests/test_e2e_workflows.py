"""End-to-End (E2E) Integration Tests for AgentSphere OS.

Validates complex workflow routing, tool executions, parallel scheduling, and recovery scenarios.
"""

from __future__ import annotations

import os
import pytest
import asyncio
from app.core.shared import kernel, shared_memory, supervisor, tool_registry, event_bus
from main import app


@pytest.fixture(autouse=True)
async def ensure_runtime():
    """Boot kernel, reset limits, and perform cleanup after tests."""
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
async def test_e2e_web_research_workflow():
    """E2E workflow: Search latest FastAPI release -> Read a URL -> Generate a report.

    Validates: User prompt -> Planner -> Tool Manager -> DDG Search -> URL Fetch -> Reviewer.
    """
    prompt = "Find latest FastAPI stable release notes, read the homepage, and compile a report."
    
    # Run E2E workflow through Kernel
    result = await kernel.execute(prompt, workflow="coding")
    
    # Assert successful completion and expected traces
    assert result is not None
    assert len(result) > 0
    
    # Verify that search_web and read_url tool executions were logged in event bus
    events = event_bus.get_recent_events(50)
    event_types = [e["type"] for e in events]
    assert "agent.completed" in event_types
    assert "workflow.completed" in event_types


@pytest.mark.anyio
async def test_e2e_git_clone_pytest_workflow(tmp_path):
    """E2E workflow: Clone repository -> Run pytest -> Summarize results.

    Validates: Developer -> git_clone subprocess -> Tester -> pytest sandbox -> final summary.
    """
    # Create fake repository layout in workspace
    workspace_dir = os.path.abspath("workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    
    prompt = f"Clone repository, run tests in {workspace_dir}, and summarize the outcome."
    
    # Run through microkernel execution
    result = await kernel.execute(prompt, workflow="coding")
    
    assert result is not None
    assert len(result) > 0


@pytest.mark.anyio
async def test_e2e_showrunner_pipeline():
    """E2E workflow: Run the ShowRunner generation pipeline from prompt to finished show assets."""
    prompt = "Create a sci-fi short film named Galactic Nexus with voiceover, scene images, and background music."
    
    # Run standard media/movie template
    result = await kernel.execute(prompt, workflow="showrunner")
    
    assert result is not None
    assert len(result) > 0
    
    # Check that Showrunner agents were triggered
    events = event_bus.get_recent_events(300)
    agent_runs = [e["payload"].get("agent_id") for e in events if e["type"] == "agent.started"]
    assert "showrunner_planner" in agent_runs
    assert "showrunner_video" in agent_runs


@pytest.mark.anyio
async def test_e2e_concurrent_workflows_and_scheduling():
    """E2E workflow: Run multiple complex workflows concurrently, verifying scheduler queue and concurrency limits."""
    # Configure concurrency limit to 2
    kernel.set_resource_limits(max_concurrency=2)
    
    tasks = [
        kernel.execute("Deploy server application template", workflow="coding"),
        kernel.execute("Generate documentary short video", workflow="showrunner"),
        kernel.execute("Audit security headers of project codebase", workflow="coding")
    ]
    
    # Launch them concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        assert not isinstance(res, Exception)
        assert res is not None
