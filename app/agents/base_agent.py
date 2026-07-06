"""Base abstractions for all AgentSphere OS agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.logger import get_logger


class BaseAgent(ABC):
    """Abstract base class for all agents managed by the supervisor."""

    def __init__(self, agent_id: str, name: str, description: str | None = None) -> None:
        self.agent_id = agent_id
        self.name = name
        self.description = description or "AgentSphere agent"
        self.logger = get_logger(f"agentsphere.agent.{agent_id}")

    @abstractmethod
    def execute(self, payload: dict[str, Any] | None = None) -> Any:
        """Execute the agent logic for the provided payload."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_id={self.agent_id!r}, name={self.name!r})"
