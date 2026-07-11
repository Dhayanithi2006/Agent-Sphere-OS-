"""Research agent for collecting context and information."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.model_router import ModelRouter
from app.llm.prompt_manager import PromptManager


class ResearcherAgent(BaseAgent):
    """Gathers information to support higher-level execution."""

    def __init__(self, prompt_manager: PromptManager | None = None, model_router: ModelRouter | None = None) -> None:
        super().__init__(agent_id="researcher", name="researcher")
        self.prompt_manager = prompt_manager or PromptManager()
        self.model_router = model_router or ModelRouter()
        self.prompt_manager.register_template("researcher", "Research the following topic: {{topic}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        topic = (payload or {}).get("topic", "")
        prompt = self.prompt_manager.render("researcher", topic=topic)
        return self.model_router.chat(task_type="researcher", prompt=prompt)
