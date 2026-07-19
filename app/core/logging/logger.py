"""Structured JSON logging utilities for the AgentSphere OS runtime."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any
from app.core.config.settings import AppSettings


class JSONFormatter(logging.Formatter):
    """Formats log records as serialized JSON strings for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize log records to JSON format."""
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Handle exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include standard attributes of interest
        log_data["filename"] = record.filename
        log_data["lineno"] = record.lineno

        # Extract extra properties supplied to the log record via the 'extra' keyword
        reserved = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName"
        }
        for key, value in record.__dict__.items():
            if key not in reserved:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logging(settings: AppSettings) -> None:
    """Configure logging handlers and formatters globally based on AppSettings."""
    root_logger = logging.getLogger()
    
    # Map configuration level to python logging level
    level_val = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(level_val)

    # Clear pre-existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Setup stdout stream handler
    stream_handler = logging.StreamHandler(sys.stdout)

    if settings.log_format.lower() == "json":
        stream_handler.setFormatter(JSONFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

    root_logger.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Helper function to fetch an application-wide logger."""
    return logging.getLogger(name)
