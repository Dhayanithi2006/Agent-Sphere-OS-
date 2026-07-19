"""Unit and integration tests for Module 3 (Supervisor Engine)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents.base_agent import BaseAgent
from app.agents.developer import DeveloperAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.checkpoint.checkpoint_manager import CheckpointManager
from app.dependency.dependency_manager import DependencyManager
from app.memory.shared_memory import SharedMemory
from app.models.task import Task, TaskStatus
from app.runtime.execution_engine import ExecutionEngine
from app.runtime.recovery import RecoveryEngine
from app.supervisor.supervisor import Supervisor
from app.core.shared import process_manager
from main import app


class EchoAgent(BaseAgent):
    """Simple agent used to validate execution flow."""

    def __init__(self) -> None:
        super().__init__(agent_id="echo", name="echo")

    def execute(self, payload: dict | None = None) -> str:
        return f"echo:{payload.get('value', '') if payload else ''}"


class FailableAgent(BaseAgent):
    """Agent that fails a specified number of times before succeeding."""

    def __init__(self) -> None:
        super().__init__(agent_id="failable", name="failable")
        self.attempts = 0

    def execute(self, payload: dict | None = None) -> str:
        self.attempts += 1
        if self.attempts < 3:
            raise ValueError("Simulated transient error")
        return "success_after_retries"


def test_shared_memory_round_trip():
    """Verify standard shared memory write/read operations."""
    memory = SharedMemory()
    memory.set("key", {"value": 42})

    assert memory.get("key")["value"] == 42
    assert memory.exists("key") is True


def test_execution_engine_runs_agent():
    """Verify execution engine runs base agent execution cycles."""
    engine = ExecutionEngine()
    agent = EchoAgent()

    result = engine.execute_agent(agent, {"value": "ok"})

    assert result.success is True
    assert result.output == "echo:ok"


@pytest.mark.anyio
async def test_supervisor_submits_and_executes_task():
    """Verify supervisor registers, creates process and executes task."""
    from app.runtime.process_repository import InMemoryProcessRepository
    from app.runtime.process_manager import ProcessManager
    local_pm = ProcessManager(InMemoryProcessRepository())
    sv = Supervisor(process_manager=local_pm)
    agent = EchoAgent()
    sv.register_agent(agent)

    task_id = await sv.submit_task("demo", agent.agent_id, {"value": "hi"})
    result = await sv.run_task(task_id)

    assert result.success is True
    assert result.output == "echo:hi"
    assert sv.get_task(task_id).status == TaskStatus.COMPLETED


def test_recovery_engine_tracks_affected_agents():
    """Verify recovery engine parses dependencies maps correctly."""
    dependency_manager = DependencyManager()
    dependency_manager.add_dependency("planner", "research")
    dependency_manager.add_dependency("developer", "planner")

    recovery_engine = RecoveryEngine(dependency_manager=dependency_manager, checkpoint_manager=CheckpointManager())

    assert recovery_engine.plan_recovery("research") == ["developer", "planner"]
    assert recovery_engine.create_checkpoint("planner", {"state": "ok"})


@pytest.mark.anyio
async def test_supervisor_tracks_processes_and_assignments():
    """Verify supervisor assigns task and maps processes properly through ProcessManager."""
    from app.runtime.process_repository import InMemoryProcessRepository
    from app.runtime.process_manager import ProcessManager
    local_pm = ProcessManager(InMemoryProcessRepository())
    sv = Supervisor(process_manager=local_pm)
    agent = EchoAgent()
    sv.register_agent(agent)

    task_id = await sv.assign_task("demo_assignment", agent.agent_id, {"value": "hi"})
    processes = await sv.list_processes()

    # Find the process mapping to our task_id
    matching_procs = [p for p in processes if p["current_task"] == "demo_assignment"]
    assert len(matching_procs) == 1
    proc = matching_procs[0]
    assert proc["agent_name"] == agent.name
    assert proc["current_state"] == "created"

    result = await sv.run_task(task_id)
    assert result.success is True

    updated_processes = await sv.list_processes()
    matching_updated = [p for p in updated_processes if p["pid"] == proc["pid"]]
    assert matching_updated[0]["current_state"] == "stopped"


def test_supervisor_routes_expose_process_and_status_endpoints():
    """Verify REST routers expose metrics and status fields."""
    client = TestClient(app)

    supervisor_response = client.get("/supervisor")
    assert supervisor_response.status_code == 200
    assert supervisor_response.json()["status"] == "running"

    assign_response = client.post(
        "/assign",
        json={"name": "demo", "agent_id": "planner", "payload": {"task": "build runtime"}},
    )
    assert assign_response.status_code == 200
    assert "task_id" in assign_response.json()

    processes_response = client.get("/processes")
    assert processes_response.status_code == 200
    assert len(processes_response.json()) >= 1

    status_response = client.get("/supervisor/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "running"


def test_assign_endpoint_executes_task_and_updates_memory_and_dependencies():
    """Verify assigning a task executes it and syncs context through memory."""
    client = TestClient(app)

    response = client.post("/assign", json={"agent": "planner", "task": "Build Todo App"})
    assert response.status_code == 200
    assert "task_id" in response.json()

    processes_response = client.get("/processes")
    processes = processes_response.json()
    assert len(processes) >= 1
    # Check that at least one process completed
    assert any(p["state"] == "COMPLETED" for p in processes)

    memory_response = client.get("/memory")
    assert memory_response.status_code == 200
    assert memory_response.json()["planner"]["goal"] == "Build Todo App"

    dependencies_response = client.get("/dependencies")
    assert dependencies_response.status_code == 200
    payload = dependencies_response.json()
    assert payload["planner"] == []
    assert payload["researcher"] == ["planner"]


@pytest.mark.anyio
async def test_intelligence_agents_execute_with_prompt_templates():
    """Verify standard agents build prompts and execute."""
    from app.runtime.process_repository import InMemoryProcessRepository
    from app.runtime.process_manager import ProcessManager
    local_pm = ProcessManager(InMemoryProcessRepository())
    sv = Supervisor(process_manager=local_pm)
    sv.register_agent(PlannerAgent())
    sv.register_agent(ResearcherAgent())
    sv.register_agent(DeveloperAgent())
    sv.register_agent(TesterAgent())
    sv.register_agent(ReviewerAgent())

    task_id = await sv.submit_task("plan", "planner", {"task": "build runtime"})
    result = await sv.run_task(task_id)

    assert result.success is True
    assert "build runtime" not in result.output.lower() or "[qwen]" in result.output


@pytest.mark.anyio
async def test_supervisor_retries_failed_tasks():
    """Verify that failed tasks are automatically retried up to max_retries."""
    from app.runtime.process_repository import InMemoryProcessRepository
    from app.runtime.process_manager import ProcessManager
    local_pm = ProcessManager(InMemoryProcessRepository())
    sv = Supervisor(process_manager=local_pm)
    agent = FailableAgent()
    sv.register_agent(agent)

    # Should succeed on the 3rd attempt (after 2 failures) because max_retries is 3
    task_id = await sv.submit_task("retry_task", agent.agent_id, {"max_retries": 3})
    result = await sv.run_task(task_id)

    assert result.success is True
    assert result.output == "success_after_retries"
    assert agent.attempts == 3
    assert sv.get_task(task_id).status == TaskStatus.COMPLETED
