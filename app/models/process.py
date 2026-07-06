"""Process-level data structures used by the runtime layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProcessStatus(str, Enum):
    """Possible lifecycle states for a runtime process."""

    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(slots=True)
class Process:
    """Simple representation of a managed runtime process."""

    process_id: str
    name: str
    status: ProcessStatus = ProcessStatus.CREATED
    metadata: dict[str, Any] = field(default_factory=dict)
