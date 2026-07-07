from app.agents.base_agent import BaseAgent
from app.models.process import ProcessStatus


class DummyAgent(BaseAgent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id=agent_id, name=agent_id)

    def execute(self, payload: dict | None = None) -> str:
        return f"done:{payload.get('value', '') if payload else ''}"


def test_base_agent_has_unique_pid_and_lifecycle_methods():
    agent_a = DummyAgent("alpha")
    agent_b = DummyAgent("beta")

    assert agent_a.pid != agent_b.pid
    assert agent_a.state == "idle"

    agent_a.start()
    assert agent_a.state == "running"

    agent_a.complete()
    assert agent_a.state == "completed"

    agent_a.reset()
    assert agent_a.state == "idle"


def test_base_agent_can_create_a_process_model():
    agent = DummyAgent("planner")
    process = agent.create_process()

    assert process.process_id == agent.pid
    assert process.name == agent.name
    assert process.status == ProcessStatus.CREATED
    assert process.metadata["agent_id"] == agent.agent_id
