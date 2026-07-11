"""Reviewer agent for policy and quality assurance."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompt_manager import PromptManager
from app.llm.qwen_client import QwenClient


class ReviewerAgent(BaseAgent):
    """Reviews outputs for quality and compliance."""

    def __init__(self, prompt_manager: PromptManager | None = None, client: QwenClient | None = None) -> None:
        super().__init__(agent_id="reviewer", name="reviewer")
        self.prompt_manager = prompt_manager or PromptManager()
        self.client = client or QwenClient()
        self.prompt_manager.register_template("reviewer", "Review the following output: {{output}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        output = (payload or {}).get("output", "")
        prompt = self.prompt_manager.render("reviewer", output=output)
        return self.client.generate(prompt)
