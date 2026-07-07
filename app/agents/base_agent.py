"""Base abstractions for all AgentSphere OS agents."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from app.core.logger import get_logger
from app.models.process import Process, ProcessStatus


class BaseAgent(ABC):
    """Abstract base class for all agents managed by the supervisor."""

    def __init__(self, agent_id: str, name: str, description: str | None = None) -> None:
        self.agent_id = agent_id
        self.name = name
        self.description = description or "AgentSphere agent"
        self.pid = str(uuid.uuid4())
        self.state = "idle"
        self.logger = get_logger(f"agentsphere.agent.{agent_id}")

    @abstractmethod
    def execute(self, payload: dict[str, Any] | None = None) -> Any:
        """Execute the agent logic for the provided payload."""

    def start(self) -> None:
        """Transition the agent into a running state."""
        self.state = "running"

    def complete(self) -> None:
        """Transition the agent into a completed state."""
        self.state = "completed"

    def reset(self) -> None:
        """Reset the agent to its idle state."""
        self.state = "idle"

    def create_process(self) -> Process:
        """Create a process model representing the agent lifecycle."""
        return Process(
            process_id=self.pid,
            name=self.name,
            status=ProcessStatus.CREATED,
            metadata={"agent_id": self.agent_id, "state": self.state},
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_id={self.agent_id!r}, name={self.name!r})"
