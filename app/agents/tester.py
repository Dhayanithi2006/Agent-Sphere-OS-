"""Tester agent for validation-oriented tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompt_manager import PromptManager
from app.llm.qwen_client import QwenClient


class TesterAgent(BaseAgent):
    """Generates validation steps or test expectations."""

    __test__ = False

    def __init__(self, prompt_manager: PromptManager | None = None, client: QwenClient | None = None) -> None:
        super().__init__(agent_id="tester", name="tester")
        self.prompt_manager = prompt_manager or PromptManager()
        self.client = client or QwenClient()
        self.prompt_manager.register_template("tester", "Create tests for: {{target}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        target = (payload or {}).get("target", "")
        prompt = self.prompt_manager.render("tester", target=target)
        return self.client.generate(prompt)
