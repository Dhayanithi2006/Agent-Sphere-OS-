"""Unit and integration tests for Kernel OS Features (Direct workflow execution, tool manager routing, resource limits, process lifecycle wrappers)."""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from typing import Any

# Force development mock mode
os.environ["QWEN_API_KEY"] = "mock-key"
os.environ["DASHSCOPE_API_KEY"] = "mock-key"
os.environ["AGENTSPHERE_ENV"] = "development"

from app.core.shared import kernel, supervisor, tool_manager, tool_registry, process_manager
from app.models.process import ProcessStatus
from main import app


@pytest.fixture(autouse=True)
async def setup_kernel():
    """Ensure kernel is booted."""
    if not kernel.is_booted:
        await kernel.boot()
    yield
    # Reset limits to defaults
    kernel.set_resource_limits(
        max_concurrency=4,
        max_tool_calls=50,
        api_budget=10.0,
        memory_limit_mb=500.0,
        timeout_seconds=120.0
    )


@pytest.mark.anyio
async def test_kernel_workflow_routing():
    """Verify that _classify_workflow correctly maps task keywords to workflows."""
    assert kernel._classify_workflow("Create a documentary on AI") == "documentary"
    assert kernel._classify_workflow("Publish a podcast interview with developer") == "podcast"
    assert kernel._classify_workflow("Build an ad commercial for a watch") == "advertisement"
    assert kernel._classify_workflow("Build a REST API in Python") == "coding"
    assert kernel._classify_workflow("Some random text movie") == "movie"


@pytest.mark.anyio
async def test_kernel_execute_coding_workflow():
    """Verify kernel.execute sequentially executes agents for the coding workflow."""
    # Run coding task
    result = await kernel.execute("Build a simple calculator", workflow="coding")
    assert result is not None
    assert len(result) > 0


@pytest.mark.anyio
async def test_resource_limits_api_budget():
    """Verify api_budget blocks execution when exceeded."""
    # Set a extremely low budget
    kernel.set_resource_limits(api_budget=0.000001)
    
    with pytest.raises(RuntimeError, match="API budget .* exceeded"):
        await kernel.execute("Build a REST API")


@pytest.mark.anyio
async def test_resource_limits_max_tool_calls():
    """Verify tool manager enforces max_tool_calls limit."""
    kernel.set_resource_limits(max_tool_calls=1)
    
    # Reset tool_manager counter
    tool_manager.tool_calls_count = 0
    
    # Register mock tool
    tool_registry.register_tool(
        tool_id="test_os_tool",
        name="Test OS Tool",
        description="A mockup tool for testing",
        func=lambda x: f"mock_value_{x}"
    )

    # First call - should succeed
    res1 = tool_manager.execute("test_os_tool", {"x": "hello"})
    assert res1 == "mock_value_hello"

    # Second call - should fail as max_tool_calls is 1
    with pytest.raises(RuntimeError, match="Maximum tool calls limit .* reached"):
        tool_manager.execute("test_os_tool", {"x": "world"})


@pytest.mark.anyio
async def test_agent_process_lifecycle_wrappers():
    """Verify kernel process lifecycle wrappers manage ProcessManager states properly."""
    # Create
    pid = await kernel.create_agent_process("planner", "Test Agent Process")
    assert pid.startswith("PID-")
    assert await process_manager.get_process_status(pid) == ProcessStatus.CREATED

    # Start
    success = await kernel.start_agent_process(pid)
    assert success is True
    assert await process_manager.get_process_status(pid) == ProcessStatus.RUNNING

    # Pause
    success = await kernel.pause_agent_process(pid)
    assert success is True
    assert await process_manager.get_process_status(pid) == ProcessStatus.SUSPENDED

    # Resume
    success = await kernel.resume_agent_process(pid)
    assert success is True
    assert await process_manager.get_process_status(pid) == ProcessStatus.RUNNING

    # Restart
    new_pid = await kernel.restart_agent_process(pid)
    assert new_pid.startswith("PID-")
    assert await process_manager.get_process_status(new_pid) == ProcessStatus.RUNNING
    # Old PID should now be killed/terminated
    assert await process_manager.get_process_status(pid) == ProcessStatus.KILLED


@pytest.mark.anyio
async def test_kernel_endpoints():
    """Verify REST API endpoints for execution and process restart."""
    with TestClient(app) as client:
        # Test execute endpoint
        resp = client.post("/kernel/execute", json={"task": "Build a REST API", "workflow": "coding"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert len(resp.json()["output"]) > 0

        # Test process restart endpoint
        # Create a process first via existing API
        response = client.post("/kernel/processes", json={"name": "test-lifecycle-agent", "metadata": {}})
        pid = response.json()["process_id"]
        
        resp_restart = client.post(f"/kernel/processes/{pid}/restart")
        assert resp_restart.status_code == 200
        assert resp_restart.json()["status"] == "ok"
        assert resp_restart.json()["new_pid"] != pid


from app.agents.base_agent import BaseAgent
from app.runtime.execution_engine import ExecutionEngine

class IterativeToolMockAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_id="iterative_mock", name="Iterative Mock Agent")
        
    def execute(self, payload: dict[str, Any] | None = None) -> str:
        payload = payload or {}
        if not payload.get("history"):
            return '{"thought": "Need latest release", "tool_required": true, "tool": "test_os_tool", "arguments": {"x": "fastapi"}}'
        else:
            tool_res = payload["history"][0]["result"]
            return f'{{"thought": "Found release: {tool_res}", "tool_required": false, "result": "Calculated value: {tool_res}"}}'


@pytest.mark.anyio
async def test_iterative_tool_execution_loop():
    """Verify that the execution engine loops on tool requests, executes tools, and records history."""
    engine = ExecutionEngine()
    agent = IterativeToolMockAgent()
    
    # Register mock tool
    tool_registry.register_tool(
        tool_id="test_os_tool",
        name="Test OS Tool",
        description="A mockup tool for testing",
        func=lambda x: f"mock_value_{x}"
    )

    payload = {"task": "Find latest fastapi release"}
    result = engine.execute_agent(agent, payload)
    
    assert result.success is True
    assert result.output == "Calculated value: mock_value_fastapi"
    
    # Verify that payload history has captured the tool call and output
    assert "history" in payload
    assert len(payload["history"]) == 1
    assert payload["history"][0]["tool"] == "test_os_tool"
    assert payload["history"][0]["result"] == "mock_value_fastapi"


