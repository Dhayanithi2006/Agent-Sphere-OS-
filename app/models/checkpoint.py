"""Checkpoint data structures for selective rollback support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Checkpoint:
    """Snapshot of an agent or task state for recovery."""

    id: str
    task_id: str
    name: str
    state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def checkpoint_id(self) -> str:
        return self.id

    @property
    def target_id(self) -> str:
        return self.task_id

    @property
    def payload(self) -> dict[str, Any]:
        return self.state

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
        }
