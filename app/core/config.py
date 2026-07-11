"""Application configuration helpers and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_DB_PATH, DEFAULT_LOG_LEVEL


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the AgentSphere OS service."""

    app_name: str = "AgentSphere OS"
    log_level: str = field(default_factory=lambda: os.getenv("AGENTSPHERE_LOG_LEVEL", DEFAULT_LOG_LEVEL))
    database_path: Path = field(default_factory=lambda: Path(os.getenv("AGENTSPHERE_DB_PATH", str(DEFAULT_DB_PATH))))
    redis_url: str | None = field(default_factory=lambda: os.getenv("AGENTSPHERE_REDIS_URL"))
    enable_metrics: bool = field(default_factory=lambda: os.getenv("AGENTSPHERE_ENABLE_METRICS", "true").lower() == "true")
    qwen_api_url: str | None = field(default_factory=lambda: os.getenv("AGENTSPHERE_QWEN_API_URL"))
    qwen_api_key: str | None = field(default_factory=lambda: os.getenv("AGENTSPHERE_QWEN_API_KEY"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("AGENTSPHERE_OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("AGENTSPHERE_OPENAI_MODEL", "gpt-4o-mini"))
    allowed_api_keys: str | None = field(default_factory=lambda: os.getenv("AGENTSPHERE_API_KEYS"))
    allowed_agents: str | None = field(default_factory=lambda: os.getenv("AGENTSPHERE_ALLOWED_AGENTS"))

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the settings."""
        return {
            "app_name": self.app_name,
            "log_level": self.log_level,
            "database_path": str(self.database_path),
            "redis_url": self.redis_url,
            "enable_metrics": self.enable_metrics,
            "qwen_api_url": self.qwen_api_url,
            "qwen_api_key": self.qwen_api_key,
            "openai_api_key": self.openai_api_key,
            "openai_model": self.openai_model,
            "allowed_api_keys": self.allowed_api_keys,
            "allowed_agents": self.allowed_agents,
        }

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the settings."""
        return {
            "app_name": self.app_name,
            "log_level": self.log_level,
            "database_path": str(self.database_path),
            "redis_url": self.redis_url,
            "enable_metrics": self.enable_metrics,
        }


settings = Settings()
