"""Checkpoint data structures for selective rollback support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Checkpoint:
    """Snapshot of an agent or task state for recovery."""

    checkpoint_id: str
    target_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
