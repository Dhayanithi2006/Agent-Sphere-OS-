"""Task models for orchestration and execution tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Any


class TaskStatus(str, Enum):
    """Execution states supported by a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Task:
    """Represents a single execution request issued to the supervisor."""

    task_id: str
    name: str
    agent_id: str
    payload: dict[str, Any] | None = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: Any = None
    error: str | None = None

    def mark_running(self) -> None:
        """Move the task into a running state."""
        self.status = TaskStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self, result: Any) -> None:
        """Move the task into a completed state with a payload."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        """Move the task into a failed state with an error message."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.updated_at = datetime.now(timezone.utc)
