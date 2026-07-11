"""Tester agent for validation-oriented tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.model_router import ModelRouter
from app.llm.prompt_manager import PromptManager


class TesterAgent(BaseAgent):
    """Generates validation steps or test expectations."""

    __test__ = False

    def __init__(self, prompt_manager: PromptManager | None = None, model_router: ModelRouter | None = None) -> None:
        super().__init__(agent_id="tester", name="tester")
        self.prompt_manager = prompt_manager or PromptManager()
        self.model_router = model_router or ModelRouter()
        self.prompt_manager.register_template("tester", "Create tests for: {{target}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        target = (payload or {}).get("target", "")
        prompt = self.prompt_manager.render("tester", target=target)
        return self.model_router.chat(task_type="tester", prompt=prompt)
