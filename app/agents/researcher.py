"""Research agent for collecting context and information."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    """Gathers information to support higher-level execution."""

    def __init__(self, model_router=None, **kwargs) -> None:
        super().__init__(agent_id="researcher", name="researcher")
        self._model_router = model_router

    def _get_router(self):
        if self._model_router:
            return self._model_router
        from app.core.shared import model_router
        return model_router

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        topic = (payload or {}).get("topic", "") or (payload or {}).get("task", "")
        prompt = f"Research the following topic: {topic}"
        return self._get_router().route("researcher", prompt)
