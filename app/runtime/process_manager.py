"""Process manager for controlling the lifecycle of agent processes."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, List, Optional
from app.models.process import Process, ProcessStatus
from app.runtime.process_repository import ProcessRepository
from app.core.logging import get_logger

logger = get_logger("agentsphere.process_manager")


class ProcessManager:
    """Core process controller for the microkernel.

    Coordinates process lifecycle (creation, suspend, resume, termination/kill)
    and enforces status transitions asynchronously.
    """

    def __init__(self, repository: ProcessRepository) -> None:
        self.repository = repository
        self._pid_counter = 1000
        self._pid_lock = asyncio.Lock()

    async def _allocate_pid(self) -> str:
        """Atomically generate a new sequential process ID."""
        async with self._pid_lock:
            self._pid_counter += 1
            return f"PID-{self._pid_counter}"

    async def create_process(self, name: str, metadata: Optional[dict[str, Any]] = None) -> Process:
        """Create and register a new process in the system."""
        pid = await self._allocate_pid()
        now = datetime.now(timezone.utc)
        process = Process(
            process_id=pid,
            name=name,
            status=ProcessStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        await self.repository.add(process)
        logger.info(
            "Kernel process created",
            extra={"pid": pid, "process_name": name, "status": process.status.value}
        )
        return process

    async def suspend_process(self, pid: str) -> bool:
        """Transition a running or created process to suspended status."""
        process = await self.repository.get(pid)
        if not process:
            logger.warning("Lifecycle operation failed: Process not found", extra={"pid": pid, "operation": "suspend"})
            return False

        if process.status not in (ProcessStatus.CREATED, ProcessStatus.RUNNING):
            logger.warning(
                "Lifecycle operation failed: Invalid state transition",
                extra={"pid": pid, "current_status": process.status.value, "operation": "suspend"}
            )
            return False

        process.status = ProcessStatus.SUSPENDED
        process.updated_at = datetime.now(timezone.utc)
        await self.repository.update(process)
        logger.info("Kernel process suspended", extra={"pid": pid, "status": process.status.value})
        return True

    async def resume_process(self, pid: str) -> bool:
        """Resume a suspended process back to running status."""
        process = await self.repository.get(pid)
        if not process:
            logger.warning("Lifecycle operation failed: Process not found", extra={"pid": pid, "operation": "resume"})
            return False

        if process.status != ProcessStatus.SUSPENDED:
            logger.warning(
                "Lifecycle operation failed: Invalid state transition",
                extra={"pid": pid, "current_status": process.status.value, "operation": "resume"}
            )
            return False

        process.status = ProcessStatus.RUNNING
        process.updated_at = datetime.now(timezone.utc)
        await self.repository.update(process)
        logger.info("Kernel process resumed", extra={"pid": pid, "status": process.status.value})
        return True

    async def kill_process(self, pid: str) -> bool:
        """Forcefully transition a process to terminal killed status."""
        process = await self.repository.get(pid)
        if not process:
            logger.warning("Lifecycle operation failed: Process not found", extra={"pid": pid, "operation": "kill"})
            return False

        terminal_states = (ProcessStatus.STOPPED, ProcessStatus.FAILED, ProcessStatus.KILLED)
        if process.status in terminal_states:
            logger.warning(
                "Lifecycle operation failed: Process is already terminal",
                extra={"pid": pid, "current_status": process.status.value, "operation": "kill"}
            )
            return False

        process.status = ProcessStatus.KILLED
        process.updated_at = datetime.now(timezone.utc)
        await self.repository.update(process)
        logger.info("Kernel process terminated/killed", extra={"pid": pid, "status": process.status.value})
        return True

    async def start_process(self, pid: str) -> bool:
        """Transition a created process to running status."""
        process = await self.repository.get(pid)
        if not process:
            logger.warning("Lifecycle operation failed: Process not found", extra={"pid": pid, "operation": "start"})
            return False

        if process.status != ProcessStatus.CREATED:
            logger.warning(
                "Lifecycle operation failed: Process must be in created state to start",
                extra={"pid": pid, "current_status": process.status.value, "operation": "start"}
            )
            return False

        process.status = ProcessStatus.RUNNING
        process.updated_at = datetime.now(timezone.utc)
        await self.repository.update(process)
        logger.info("Kernel process started", extra={"pid": pid, "status": process.status.value})
        return True

    async def complete_process(self, pid: str) -> bool:
        """Transition a running process to completed (stopped) status."""
        process = await self.repository.get(pid)
        if not process:
            logger.warning("Lifecycle operation failed: Process not found", extra={"pid": pid, "operation": "complete"})
            return False

        if process.status != ProcessStatus.RUNNING:
            logger.warning(
                "Lifecycle operation failed: Process must be in running state to complete",
                extra={"pid": pid, "current_status": process.status.value, "operation": "complete"}
            )
            return False

        process.status = ProcessStatus.STOPPED
        process.updated_at = datetime.now(timezone.utc)
        await self.repository.update(process)
        logger.info("Kernel process completed", extra={"pid": pid, "status": process.status.value})
        return True

    async def fail_process(self, pid: str) -> bool:
        """Transition a running process to failed status."""
        process = await self.repository.get(pid)
        if not process:
            logger.warning("Lifecycle operation failed: Process not found", extra={"pid": pid, "operation": "fail"})
            return False

        if process.status != ProcessStatus.RUNNING:
            logger.warning(
                "Lifecycle operation failed: Process must be in running state to fail",
                extra={"pid": pid, "current_status": process.status.value, "operation": "fail"}
            )
            return False

        process.status = ProcessStatus.FAILED
        process.updated_at = datetime.now(timezone.utc)
        await self.repository.update(process)
        logger.info("Kernel process failed", extra={"pid": pid, "status": process.status.value})
        return True

    async def get_process_status(self, pid: str) -> Optional[ProcessStatus]:
        """Fetch the current status of a process."""
        process = await self.repository.get(pid)
        return process.status if process else None

    async def list_processes(self) -> List[Process]:
        """Retrieve all registered processes in the system."""
        return await self.repository.list()

