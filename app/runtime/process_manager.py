"""Process manager for stateful runtime process tracking."""

from __future__ import annotations

from typing import Any

from app.models.process import Process, ProcessStatus


class ProcessManager:
    """Manages process lifecycle metadata for the runtime."""

    def __init__(self) -> None:
        self._processes: dict[str, Process] = {}

    def add_process(self, process: Process) -> None:
        self._processes[process.process_id] = process

    def get_process(self, process_id: str) -> Process | None:
        return self._processes.get(process_id)

    def list_processes(self) -> list[Process]:
        return list(self._processes.values())

    def update_process(self, process_id: str, *, status: ProcessStatus | None = None, metadata: dict[str, Any] | None = None) -> None:
        process = self.get_process(process_id)
        if process is None:
            return
        if status is not None:
            process.status = status
        if metadata is not None:
            process.metadata.update(metadata)
