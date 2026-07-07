from app.runtime.execution_engine import ExecutionEngine, ExecutionResult
from app.agents.base_agent import BaseAgent


class EchoAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_id='echo', name='echo')

    def execute(self, payload: dict | None = None) -> str:
        return f"echo:{payload.get('value', '') if payload else ''}"


def test_module4_execution_engine_executes_and_queues():
    engine = ExecutionEngine()
    agent = EchoAgent()
    result = engine.execute_agent(agent, {'value': 'ok'})
    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.output == 'echo:ok'

    engine.enqueue_task(agent, {'value': 'queued'})
    queued = engine.dispatch_next()
    assert queued.output == 'echo:queued'
