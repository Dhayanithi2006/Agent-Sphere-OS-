"""Health router exposing runtime metadata and health status."""

from __future__ import annotations

import sys
import time
from fastapi import APIRouter, Depends
from app.core.config import AppSettings, get_settings

router = APIRouter()

# Global process start time to compute system uptime
START_TIME = time.time()


@router.get("/health")
def health_check(settings: AppSettings = Depends(get_settings)) -> dict[str, object]:
    """Retrieve operational health, uptime, and settings context."""
    uptime = time.time() - START_TIME
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(uptime, 2),
        "python_version": sys.version,
        "log_level": settings.log_level,
    }
