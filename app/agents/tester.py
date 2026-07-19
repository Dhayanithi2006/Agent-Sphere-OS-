"""Tester agent for validation-oriented tasks."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent


class TesterAgent(BaseAgent):
    """Generates validation steps or test expectations."""

    __test__ = False  # Prevent pytest from collecting this class as a test

    def __init__(self, model_router=None, **kwargs) -> None:
        super().__init__(agent_id="tester", name="tester")
        self._model_router = model_router

    def _get_router(self):
        if self._model_router:
            return self._model_router
        from app.core.shared import model_router
        return model_router

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        target = (payload or {}).get("target", "") or (payload or {}).get("task", "")
        prompt = f"Create tests for: {target}"
        return self._get_router().route("default", prompt)
