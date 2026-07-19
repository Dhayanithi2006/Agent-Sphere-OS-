"""Unit and integration tests for Module 1 (Runtime Environment)."""

from __future__ import annotations

import json
import logging
from io import StringIO
from fastapi.testclient import TestClient

from app.core.config import AppSettings, get_settings
from app.core.logging.logger import JSONFormatter, setup_logging
from app.core.bootstrap import AppBootstrap
from main import app


def test_settings_load_defaults():
    """Verify configuration loads correct defaults."""
    settings = AppSettings()
    assert settings.app_name == "AgentSphere OS"
    assert settings.app_version == "4.0.0"
    assert settings.environment == "production"
    assert settings.log_level == "INFO"


def test_settings_override_via_env(monkeypatch):
    """Verify environment variables take precedence in settings."""
    monkeypatch.setenv("APP_NAME", "Test Kernel OS")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = AppSettings()
    assert settings.app_name == "Test Kernel OS"
    assert settings.environment == "testing"
    assert settings.log_level == "DEBUG"


def test_json_logging_format():
    """Verify logger output is valid JSON and contains required structured keys."""
    # Capture log output
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger("test_json_log")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logger.info("Test structured logging message", extra={"correlation_id": "123-abc"})

    log_output = log_capture.getvalue().strip()
    assert log_output != ""
    
    # Parse as JSON
    parsed = json.loads(log_output)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_json_log"
    assert parsed["message"] == "Test structured logging message"
    assert parsed["correlation_id"] == "123-abc"
    assert "timestamp" in parsed
    assert "filename" in parsed
    assert "lineno" in parsed


def test_health_endpoint():
    """Verify health endpoint returns 200 OK with correct schema."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == "AgentSphere OS"
        assert data["version"] == "4.0.0"
        assert "uptime_seconds" in data
        assert "python_version" in data


from unittest.mock import patch


def test_bootstrap_lifespan():
    """Verify application lifespans fire boot and shutdown logs."""
    settings = AppSettings(environment="testing", log_level="DEBUG")
    boot = AppBootstrap(settings)
    test_app = boot.create_app()

    with patch("app.core.bootstrap.logger") as mock_logger:
        with TestClient(test_app) as _:
            # Startup logs should have run
            pass
        # Shutdown logs should have run
    
    # Verify info logs were called with start/stop strings
    info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    assert any("Booting AgentSphere OS" in msg for msg in info_calls)
    assert any("shutting down AgentSphere OS" in msg for msg in info_calls)

