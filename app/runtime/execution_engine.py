"""Execution engine responsible for running managed agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.logger import get_logger


@dataclass(slots=True)
class ExecutionResult:
    """Outcome of an agent execution attempt."""

    success: bool
    output: Any = None
    error: str | None = None
    agent_id: str | None = None


class ExecutionEngine:
    """Executes agents and captures their outcomes."""

    def __init__(self) -> None:
        self.logger = get_logger("agentsphere.execution_engine")

    def execute_agent(self, agent: BaseAgent, payload: dict[str, Any] | None = None) -> ExecutionResult:
        """Run an agent and return a structured result."""
        self.logger.info("Executing agent %s", agent.agent_id)
        try:
            output = agent.execute(payload)
            return ExecutionResult(success=True, output=output, agent_id=agent.agent_id)
        except Exception as exc:  # pragma: no cover - defensive path
            self.logger.exception("Agent %s failed", agent.agent_id)
            return ExecutionResult(success=False, error=str(exc), agent_id=agent.agent_id)
