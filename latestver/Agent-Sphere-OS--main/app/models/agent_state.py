"""Agent state primitives used by the supervisor and runtime modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Lifecycle status values for agent execution."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(slots=True)
class AgentState:
    """Mutable state for a managed agent process."""

    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    metadata: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None

    def mark_running(self) -> None:
        """Mark the agent as running."""
        self.status = AgentStatus.RUNNING

    def mark_completed(self) -> None:
        """Mark the agent as completed."""
        self.status = AgentStatus.COMPLETED

    def mark_failed(self, error: str | None = None) -> None:
        """Mark the agent as failed with an optional error message."""
        self.status = AgentStatus.FAILED
        self.last_error = error
