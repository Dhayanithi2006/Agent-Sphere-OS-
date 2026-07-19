import pytest
from app.supervisor.supervisor import Supervisor


class EchoAgent:
    def __init__(self) -> None:
        self.agent_id = 'echo'
        self.name = 'echo'

    def execute(self, payload: dict | None = None) -> str:
        return 'ok'


@pytest.mark.anyio
async def test_module2_supervisor_can_submit_and_run_tasks():
    supervisor = Supervisor()
    agent = EchoAgent()
    supervisor.register_agent(agent)
    task_id = await supervisor.submit_task('demo', agent.agent_id, {'value': 'hi'})
    result = await supervisor.run_task(task_id)
    assert result.success is True
    assert supervisor.get_task(task_id).status.value == 'completed'

