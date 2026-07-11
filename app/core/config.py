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

    # Qwen Cloud Settings
    qwen_base_url: str = field(default_factory=lambda: os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    qwen_api_key: str | None = field(default_factory=lambda: os.getenv("QWEN_API_KEY"))
    qwen_model: str = field(default_factory=lambda: os.getenv("QWEN_MODEL", "qwen-turbo"))
    qwen_max_retries: int = field(default_factory=lambda: int(os.getenv("QWEN_MAX_RETRIES", "3")))
    qwen_timeout: float = field(default_factory=lambda: float(os.getenv("QWEN_TIMEOUT", "60.0")))

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the settings."""
        return {
            "app_name": self.app_name,
            "log_level": self.log_level,
            "database_path": str(self.database_path),
            "redis_url": self.redis_url,
            "enable_metrics": self.enable_metrics,
            "qwen_base_url": self.qwen_base_url,
            "qwen_model": self.qwen_model,
            "qwen_max_retries": self.qwen_max_retries,
            "qwen_timeout": self.qwen_timeout,
        }


settings = Settings()
