"""Configuration module exports and dependency providers."""

from __future__ import annotations

from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

from app.core.config.settings import AppSettings

# Instantiate configuration globally
settings = AppSettings()


@lru_cache
def get_settings() -> AppSettings:
    """Dependency injection helper to retrieve settings (cached for efficiency)."""
    return settings
