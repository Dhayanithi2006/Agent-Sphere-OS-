"""Reviewer agent for policy and quality assurance."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.model_router import ModelRouter
from app.llm.prompt_manager import PromptManager


class ReviewerAgent(BaseAgent):
    """Reviews outputs for policy and compliance."""

    def __init__(self, prompt_manager: PromptManager | None = None, model_router: ModelRouter | None = None) -> None:
        super().__init__(agent_id="reviewer", name="reviewer")
        self.prompt_manager = prompt_manager or PromptManager()
        self.model_router = model_router or ModelRouter()
        self.prompt_manager.register_template("reviewer", "Review the following output: {{output}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        output = (payload or {}).get("output", "")
        prompt = self.prompt_manager.render("reviewer", output=output)
        return self.model_router.chat(task_type="reviewer", prompt=prompt)
