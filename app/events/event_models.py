"""Pydantic schemas and priority enumerations for runtime events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class EventPriority(int, Enum):
    """Priority ranks determining the scheduling weight of an event."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2


class Event(BaseModel):
    """Core Event data structure representation."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    payload: Optional[Any] = None
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retries: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event structure into a standard dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "retries": self.retries,
            "error": self.error,
        }
