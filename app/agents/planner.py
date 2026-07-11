"""Planner agent for orchestrating high-level tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.model_router import ModelRouter
from app.llm.prompt_manager import PromptManager


class PlannerAgent(BaseAgent):
    """Produces a structured plan for a work request."""

    def __init__(self, prompt_manager: PromptManager | None = None, model_router: ModelRouter | None = None) -> None:
        super().__init__(agent_id="planner", name="planner")
        self.prompt_manager = prompt_manager or PromptManager()
        self.model_router = model_router or ModelRouter()
        self.prompt_manager.register_template("planner", "Plan the following task: {{task}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        task = (payload or {}).get("task", "")
        prompt = self.prompt_manager.render("planner", task=task)
        return self.model_router.chat(task_type="planner", prompt=prompt)
