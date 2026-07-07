"""Execution engine responsible for running managed agents."""

from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.logger import get_logger


@dataclass(slots=True)
class ExecutionResult:
    """Outcome of an agent execution attempt."""

    success: bool
    output: Any = None
    error: str | None = None
    agent_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionEngine:
    """Executes agents and captures their outcomes."""

    def __init__(self) -> None:
        self.logger = get_logger("agentsphere.execution_engine")
        self._queue: deque[tuple[BaseAgent, dict[str, Any] | None]] = deque()
        self._history: list[dict[str, Any]] = []
        self._metrics: dict[str, int] = {"total_executions": 0, "success_count": 0, "failure_count": 0}
        self._processes: dict[str, dict[str, Any]] = {}

    def execute_agent(self, agent: BaseAgent, payload: dict[str, Any] | None = None) -> ExecutionResult:
        """Run an agent and return a structured result."""
        self.logger.info("Executing agent %s", agent.agent_id)
        try:
            output = agent.execute(payload)
            result = ExecutionResult(success=True, output=output, agent_id=agent.agent_id)
            self._record_execution(agent.agent_id, result)
            return result
        except Exception as exc:  # pragma: no cover - defensive path
            self.logger.exception("Agent %s failed", agent.agent_id)
            result = ExecutionResult(success=False, error=str(exc), agent_id=agent.agent_id)
            self._record_execution(agent.agent_id, result)
            return result

    def execute_sequential(self, agents: list[BaseAgent], payloads: list[dict[str, Any] | None] | None = None) -> list[ExecutionResult]:
        """Execute a list of agents one after another."""
        payloads = payloads or [None] * len(agents)
        return [self.execute_agent(agent, payload) for agent, payload in zip(agents, payloads)]

    def execute_parallel(self, agents: list[BaseAgent], payloads: list[dict[str, Any] | None] | None = None) -> list[ExecutionResult]:
        """Execute a list of agents in parallel using a thread pool."""
        payloads = payloads or [None] * len(agents)
        with ThreadPoolExecutor(max_workers=max(1, len(agents))) as executor:
            futures = [executor.submit(self.execute_agent, agent, payload) for agent, payload in zip(agents, payloads)]
            return [future.result() for future in futures]

    def enqueue_task(self, agent: BaseAgent, payload: dict[str, Any] | None = None) -> None:
        """Queue a task for later dispatch."""
        self._queue.append((agent, payload))
        self._processes[agent.agent_id] = {"agent_id": agent.agent_id, "status": "queued", "payload": payload}

    def dispatch_next(self) -> ExecutionResult:
        """Dispatch the next queued task."""
        if not self._queue:
            raise IndexError("Execution queue is empty")
        agent, payload = self._queue.popleft()
        self._processes[agent.agent_id] = {"agent_id": agent.agent_id, "status": "running", "payload": payload}
        result = self.execute_agent(agent, payload)
        self._processes[agent.agent_id] = {"agent_id": agent.agent_id, "status": "completed" if result.success else "failed", "payload": payload}
        return result

    def queue_size(self) -> int:
        """Return the number of queued tasks."""
        return len(self._queue)

    def get_processes(self) -> list[dict[str, Any]]:
        """Return currently tracked process metadata."""
        return list(self._processes.values())

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Return execution history entries."""
        return list(self._history)

    def get_metrics(self) -> dict[str, int]:
        """Return runtime metrics."""
        return dict(self._metrics)

    def _record_execution(self, agent_id: str, result: ExecutionResult) -> None:
        self._metrics["total_executions"] += 1
        if result.success:
            self._metrics["success_count"] += 1
        else:
            self._metrics["failure_count"] += 1
        self._history.append(
            {
                "agent_id": agent_id,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "timestamp": result.timestamp,
            }
        )
