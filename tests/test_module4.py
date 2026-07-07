from app.runtime.execution_engine import ExecutionEngine
from app.agents.base_agent import BaseAgent


class DummyAgent(BaseAgent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id=agent_id, name=agent_id)

    def execute(self, payload: dict | None = None) -> str:
        return f"done:{payload.get('value', '') if payload else ''}"


def test_execution_engine_dispatches_in_order():
    engine = ExecutionEngine()
    agent = DummyAgent("planner")

    engine.enqueue_task(agent, {"value": "start"})
    result = engine.dispatch_next()

    assert result.success is True
    assert result.output == "done:start"
    assert engine.queue_size() == 0
