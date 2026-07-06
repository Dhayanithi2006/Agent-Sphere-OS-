import pytest

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


class EchoAgent(BaseAgent):
    """Simple agent used to validate execution flow."""

    def __init__(self):
        super().__init__(agent_id="echo", name="echo")

    def execute(self, payload: dict | None = None) -> str:
        return f"echo:{payload.get('value', '') if payload else ''}"


def test_shared_memory_round_trip():
    memory = SharedMemory()
    memory.set("key", {"value": 42})

    assert memory.get("key")["value"] == 42
    assert memory.exists("key") is True


def test_execution_engine_runs_agent():
    engine = ExecutionEngine()
    agent = EchoAgent()

    result = engine.execute_agent(agent, {"value": "ok"})

    assert result.success is True
    assert result.output == "echo:ok"


def test_supervisor_submits_and_executes_task():
    supervisor = Supervisor()
    agent = EchoAgent()
    supervisor.register_agent(agent)

    task_id = supervisor.submit_task("demo", agent.agent_id, {"value": "hi"})
    result = supervisor.run_task(task_id)

    assert result.success is True
    assert result.output == "echo:hi"
    assert supervisor.get_task(task_id).status == TaskStatus.COMPLETED


def test_recovery_engine_tracks_affected_agents():
    dependency_manager = DependencyManager()
    dependency_manager.add_dependency("planner", "research")
    dependency_manager.add_dependency("developer", "planner")

    recovery_engine = RecoveryEngine(dependency_manager=dependency_manager, checkpoint_manager=CheckpointManager())

    assert recovery_engine.plan_recovery("research") == ["developer", "planner"]
    assert recovery_engine.create_checkpoint("planner", {"state": "ok"})


def test_intelligence_agents_execute_with_prompt_templates():
    supervisor = Supervisor()
    supervisor.register_agent(PlannerAgent())
    supervisor.register_agent(ResearcherAgent())
    supervisor.register_agent(DeveloperAgent())
    supervisor.register_agent(TesterAgent())
    supervisor.register_agent(ReviewerAgent())

    task_id = supervisor.submit_task("plan", "planner", {"task": "build runtime"})
    result = supervisor.run_task(task_id)

    assert result.success is True
    assert "build runtime" not in result.output.lower() or "[qwen]" in result.output
