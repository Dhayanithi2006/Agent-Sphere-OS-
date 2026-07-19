"""Dynamic Agent Factory: Creates and destroys ephemeral helper agents at runtime."""

from __future__ import annotations

from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import supervisor
from app.core.logger import get_logger

logger = get_logger("agentsphere.core.dynamic_agent")


class DynamicAgent(BaseAgent):
    """An ephemeral dynamic agent registered and destroyed on-demand for transient operations."""

    def __init__(self, agent_id: str, prompt_template: str, task_type: str = "default") -> None:
        super().__init__(agent_id=agent_id, name=agent_id, description=f"Transient Dynamic Agent: {agent_id}")
        self.prompt_template = prompt_template
        self.task_type = task_type

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info(f"Executing transient dynamic agent: {self.agent_id}")
        input_data = (payload or {}).get("task", "") or (payload or {}).get("input", "")

        # Format prompt instruction
        full_prompt = f"{self.prompt_template}\n\nTask Input:\n{input_data}"

        from app.core.shared import model_router
        response = model_router.generate(full_prompt, self.task_type)
        return response


def spawn_dynamic_agent(agent_id: str, prompt_template: str, task_type: str = "default") -> DynamicAgent:
    """Instantiate and register a dynamic agent into the supervisor."""
    agent = DynamicAgent(agent_id, prompt_template, task_type)
    supervisor.register_agent(agent)
    logger.info(f"Successfully spawned and registered transient agent: {agent_id}")
    return agent


def destroy_dynamic_agent(agent_id: str) -> None:
    """Unregister and garbage collect a transient agent."""
    if agent_id in supervisor._agents:
        del supervisor._agents[agent_id]
        logger.info(f"Successfully destroyed and unregistered transient agent: {agent_id}")
