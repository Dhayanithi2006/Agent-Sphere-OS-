"""Runtime lifecycle support for the AgentSphere OS kernel."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.runtime.process_manager import ProcessManager


class Lifecycle:
    """A lifecycle manager that controls runtime start/stop behavior."""

    def __init__(self) -> None:
        self.logger = get_logger("agentsphere.runtime.lifecycle")
        self.process_manager = ProcessManager()
        self.is_running = False

    def start(self) -> None:
        self.logger.info("Starting runtime lifecycle")
        self.is_running = True

    def stop(self) -> None:
        self.logger.info("Stopping runtime lifecycle")
        self.is_running = False

    def register_process(self, process: Any) -> None:
        self.process_manager.add_process(process)

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self.is_running,
            "process_count": len(self.process_manager.list_processes()),
        }
