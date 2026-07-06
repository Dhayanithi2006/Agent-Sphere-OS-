"""Research agent for collecting context and information."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.prompt_manager import PromptManager
from app.llm.qwen_client import QwenClient


class ResearcherAgent(BaseAgent):
    """Gathers information to support higher-level execution."""

    def __init__(self, prompt_manager: PromptManager | None = None, client: QwenClient | None = None) -> None:
        super().__init__(agent_id="researcher", name="researcher")
        self.prompt_manager = prompt_manager or PromptManager()
        self.client = client or QwenClient()
        self.prompt_manager.register_template("researcher", "Research the following topic: {{topic}}")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        topic = (payload or {}).get("topic", "")
        prompt = self.prompt_manager.render("researcher", topic=topic)
        return self.client.generate(prompt)
