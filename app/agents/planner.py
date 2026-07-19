"""Planner agent for orchestrating high-level tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """Produces a structured plan for a work request."""

    def __init__(self, model_router=None, **kwargs) -> None:
        super().__init__(agent_id="planner", name="planner")
        self._model_router = model_router

    def _get_router(self):
        if self._model_router:
            return self._model_router
        from app.core.shared import model_router
        return model_router

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        task = (payload or {}).get("task", "")
        prompt = f"Plan the following task: {task}"
        return self._get_router().route("planner", prompt)
