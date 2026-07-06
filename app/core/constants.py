"""Central constants for the AgentSphere OS runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_DB_PATH: Final[Path] = PROJECT_ROOT / "data" / "agentsphere.db"
DEFAULT_MEMORY_NAMESPACE: Final[str] = "default"
