from app.supervisor.supervisor import Supervisor


class EchoAgent:
    def __init__(self) -> None:
        self.agent_id = 'echo'
        self.name = 'echo'

    def execute(self, payload: dict | None = None) -> str:
        return 'ok'


def test_module2_supervisor_can_submit_and_run_tasks():
    supervisor = Supervisor()
    agent = EchoAgent()
    supervisor.register_agent(agent)
    task_id = supervisor.submit_task('demo', agent.agent_id, {'value': 'hi'})
    result = supervisor.run_task(task_id)
    assert result.success is True
    assert supervisor.get_task(task_id).status.value == 'completed'
