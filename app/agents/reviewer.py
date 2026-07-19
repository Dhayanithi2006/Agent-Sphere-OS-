"""Reviewer agent for policy and quality assurance."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent


class ReviewerAgent(BaseAgent):
    """Reviews outputs for quality and compliance."""

    def __init__(self, model_router=None, **kwargs) -> None:
        super().__init__(agent_id="reviewer", name="reviewer")
        self._model_router = model_router

    def _get_router(self):
        if self._model_router:
            return self._model_router
        from app.core.shared import model_router
        return model_router

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        output = (payload or {}).get("output", "") or (payload or {}).get("task", "")
        prompt = f"Review the following output: {output}"
        return self._get_router().route("reviewer", prompt)
