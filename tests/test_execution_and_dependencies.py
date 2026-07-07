from app.agents.base_agent import BaseAgent
from app.dependency.dependency_manager import DependencyManager
from app.runtime.execution_engine import ExecutionEngine, ExecutionResult


class EchoAgent(BaseAgent):
    def __init__(self, agent_id: str = "echo") -> None:
        super().__init__(agent_id=agent_id, name=agent_id)

    def execute(self, payload: dict | None = None) -> str:
        return f"echo:{payload.get('value', '') if payload else ''}"


def test_execution_engine_supports_sequential_and_parallel_execution():
    engine = ExecutionEngine()
    agents = [EchoAgent("echo-1"), EchoAgent("echo-2")]

    sequential_results = engine.execute_sequential(agents, [{"value": "a"}, {"value": "b"}])
    assert [result.output for result in sequential_results] == ["echo:a", "echo:b"]

    parallel_results = engine.execute_parallel(agents, [{"value": "x"}, {"value": "y"}])
    assert [result.output for result in parallel_results] == ["echo:x", "echo:y"]


def test_execution_engine_handles_queue_and_metrics():
    engine = ExecutionEngine()
    agent = EchoAgent()

    engine.enqueue_task(agent, {"value": "queued"})
    assert engine.queue_size() == 1

    result = engine.dispatch_next()
    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.output == "echo:queued"
    assert engine.queue_size() == 0

    history = engine.get_execution_history()
    assert len(history) == 1
    assert history[0]["agent_id"] == agent.agent_id

    metrics = engine.get_metrics()
    assert metrics["total_executions"] == 1
    assert metrics["success_count"] == 1


def test_dependency_manager_tracks_graph_and_cycles():
    manager = DependencyManager()
    manager.add_dependency("planner", "research")
    manager.add_dependency("developer", "planner")

    assert manager.get_dependencies("planner") == {"research"}
    assert manager.get_dependents("planner") == {"developer"}
    assert manager.get_affected_agents("research") == {"planner", "developer"}

    manager.add_dependency("alpha", "beta")
    manager.add_dependency("beta", "alpha")
    assert manager.has_cycle() is True

    dot = manager.to_dot()
    assert "digraph" in dot
    assert "planner" in dot
