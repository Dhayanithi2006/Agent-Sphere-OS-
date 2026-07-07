"""Developer agent for implementation-oriented tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompt_manager import PromptManager
from app.llm.qwen_client import QwenClient


class DeveloperAgent(BaseAgent):
    """Produces implementation guidance or code-like output."""

    def __init__(self, prompt_manager: PromptManager | None = None, client: QwenClient | None = None) -> None:
        super().__init__(agent_id="developer", name="developer")
        self.prompt_manager = prompt_manager or PromptManager()
        self.client = client or QwenClient()
        self.prompt_manager.register_template("developer", "Implement the following requirement: {{requirement}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        requirement = (payload or {}).get("requirement", "")
        prompt = self.prompt_manager.render("developer", requirement=requirement)
        return self.client.generate(prompt)
