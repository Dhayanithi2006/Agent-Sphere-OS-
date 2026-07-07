"""Planner agent for orchestrating high-level tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompt_manager import PromptManager
from app.llm.qwen_client import QwenClient


class PlannerAgent(BaseAgent):
    """Produces a structured plan for a work request."""

    def __init__(self, prompt_manager: PromptManager | None = None, client: QwenClient | None = None) -> None:
        super().__init__(agent_id="planner", name="planner")
        self.prompt_manager = prompt_manager or PromptManager()
        self.client = client or QwenClient()
        self.prompt_manager.register_template("planner", "Plan the following task: {{task}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        task = (payload or {}).get("task", "")
        prompt = self.prompt_manager.render("planner", task=task)
        return self.client.generate(prompt)
