from app.agents.base_agent import BaseAgent
from app.models.process import ProcessStatus


class EchoAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_id='echo', name='echo')

    def execute(self, payload: dict | None = None) -> str:
        return 'ok'


def test_module1_runtime_basics():
    agent = EchoAgent()
    assert agent.agent_id == 'echo'
    assert agent.state == 'idle'
    agent.start()
    assert agent.state == 'running'
    agent.complete()
    assert agent.state == 'completed'
    proc = agent.create_process()
    assert proc.status == ProcessStatus.CREATED
    assert proc.metadata['agent_id'] == 'echo'
