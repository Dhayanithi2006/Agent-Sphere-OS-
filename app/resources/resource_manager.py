"""Resource manager for tracking system health and enforcing memory/CPU limits on processes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.core.logging import get_logger

try:
    import psutil
except ImportError:
    psutil = None

logger = get_logger("agentsphere.resources")

EVENT_RESOURCE_LIMIT_EXCEEDED = "ResourceLimitExceeded"


class ResourceManager:
    """Monitors system-wide resource utilization and throttles/suspends process PIDs exceeding thresholds."""

    def __init__(self, process_manager: Optional[Any] = None, event_bus: Optional[Any] = None) -> None:
        try:
            from app.core.shared import process_manager as shared_pm, event_bus as shared_eb
        except ImportError:
            shared_pm = None
            shared_eb = None

        self.process_manager = process_manager or shared_pm
        self.event_bus = event_bus or shared_eb

        # Dict mapping pid -> {os_pid, cpu_limit, memory_limit_mb}
        self._registered: Dict[str, Dict[str, Any]] = {}
        # Dict mapping pid -> {cpu, memory_mb} for simulated test usage
        self._virtual_usage: Dict[str, Dict[str, float]] = {}

    def get_system_metrics(self) -> Dict[str, Any]:
        """Collect and return CPU, Memory, Disk usage metrics."""
        if psutil is not None:
            try:
                cpu_pct = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                return {
                    "cpu_percent": cpu_pct,
                    "memory": {
                        "total": mem.total,
                        "used": mem.used,
                        "free": mem.free,
                        "percent": mem.percent,
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": disk.percent,
                    },
                }
            except Exception as e:
                logger.warning(f"Failed to query psutil metrics: {e}")

        # Stub fallback when psutil is missing or raises an OS error
        return {
            "cpu_percent": 15.0,
            "memory": {
                "total": 16 * 1024 * 1024 * 1024,
                "used": 6 * 1024 * 1024 * 1024,
                "free": 10 * 1024 * 1024 * 1024,
                "percent": 37.5,
            },
            "disk": {
                "total": 512 * 1024 * 1024 * 1024,
                "used": 128 * 1024 * 1024 * 1024,
                "free": 384 * 1024 * 1024 * 1024,
                "percent": 25.0,
            },
        }

    def register_process(
        self,
        pid: str,
        os_pid: Optional[int] = None,
        cpu_limit: float = 80.0,
        memory_limit_mb: float = 500.0,
    ) -> None:
        """Register a process PID and its corresponding limits for resource monitoring."""
        self._registered[pid] = {
            "os_pid": os_pid,
            "cpu_limit": cpu_limit,
            "memory_limit_mb": memory_limit_mb,
        }
        logger.info(f"Registered process {pid} for monitoring (CPU limit={cpu_limit}%, Memory limit={memory_limit_mb}MB)")

    def unregister_process(self, pid: str) -> None:
        """Stop tracking a process."""
        self._registered.pop(pid, None)
        self._virtual_usage.pop(pid, None)
        logger.info(f"Unregistered process {pid}")

    def set_virtual_usage(self, pid: str, cpu: float, memory_mb: float) -> None:
        """Manually specify resource utilization metrics for testing simulated processes."""
        self._virtual_usage[pid] = {"cpu": cpu, "memory_mb": memory_mb}

    async def check_limits(self) -> List[str]:
        """Check registered processes against limits. Suspend violators and broadcast warning alerts."""
        suspended = []

        for pid, conf in list(self._registered.items()):
            cpu, mem_mb = 0.0, 0.0

            # 1. Resolve virtual metrics if set (primarily for tests)
            if pid in self._virtual_usage:
                cpu = self._virtual_usage[pid]["cpu"]
                mem_mb = self._virtual_usage[pid]["memory_mb"]
            # 2. Check actual OS-level metrics using psutil
            elif conf["os_pid"] is not None and psutil is not None:
                try:
                    p = psutil.Process(conf["os_pid"])
                    cpu = p.cpu_percent(interval=None)
                    mem_mb = p.memory_info().rss / (1024 * 1024)
                except Exception as e:
                    logger.debug(f"Failed to check resources for OS process {conf['os_pid']}: {e}")

            # 3. Check thresholds
            cpu_exceeded = cpu > conf["cpu_limit"]
            mem_exceeded = mem_mb > conf["memory_limit_mb"]

            if cpu_exceeded or mem_exceeded:
                msg = (
                    f"Process {pid} exceeded resource limits: "
                    f"CPU={cpu:.1f}% (limit={conf['cpu_limit']}%), "
                    f"Memory={mem_mb:.1f}MB (limit={conf['memory_limit_mb']}MB)"
                )
                logger.warning(msg)

                # Broadcast warning alert
                if self.event_bus:
                    try:
                        self.event_bus.publish(
                            EVENT_RESOURCE_LIMIT_EXCEEDED,
                            {"pid": pid, "cpu_percent": cpu, "memory_mb": mem_mb, "details": msg}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish limit warning: {e}")

                # Execute suspension flow
                if self.process_manager:
                    try:
                        success = await self.process_manager.suspend_process(pid)
                        if success:
                            suspended.append(pid)
                    except Exception as e:
                        logger.error(f"Failed to suspend resource violator process {pid}: {e}")

        return suspended
