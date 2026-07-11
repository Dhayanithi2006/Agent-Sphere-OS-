"""Developer agent for implementation-oriented tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.model_router import ModelRouter
from app.llm.prompt_manager import PromptManager


class DeveloperAgent(BaseAgent):
    """Produces implementation guidance or code-like output."""

    def __init__(self, prompt_manager: PromptManager | None = None, model_router: ModelRouter | None = None) -> None:
        super().__init__(agent_id="developer", name="developer")
        self.prompt_manager = prompt_manager or PromptManager()
        self.model_router = model_router or ModelRouter()
        self.prompt_manager.register_template("developer", "Implement the following requirement: {{requirement}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        requirement = (payload or {}).get("requirement", "")
        prompt = self.prompt_manager.render("developer", requirement=requirement)
        return self.model_router.chat(task_type="developer", prompt=prompt)
