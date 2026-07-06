"""Supervisor engine that manages agent execution as OS-like processes."""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.logger import get_logger
from app.memory.shared_memory import SharedMemory
from app.models.task import Task, TaskStatus
from app.runtime.execution_engine import ExecutionEngine, ExecutionResult


class Supervisor:
    """Coordinates task submission, lifecycle handling, and execution."""

    def __init__(self, shared_memory: SharedMemory | None = None, execution_engine: ExecutionEngine | None = None) -> None:
        self.logger = get_logger("agentsphere.supervisor")
        self.shared_memory = shared_memory or SharedMemory()
        self.execution_engine = execution_engine or ExecutionEngine()
        self._agents: dict[str, BaseAgent] = {}
        self._tasks: dict[str, Task] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent so it can be used by the supervisor."""
        self._agents[agent.agent_id] = agent
        self.logger.info("Registered agent %s", agent.agent_id)

    def submit_task(self, name: str, agent_id: str, payload: dict[str, Any] | None = None) -> str:
        """Create and register a new task for execution."""
        task_id = str(uuid.uuid4())
        task = Task(task_id=task_id, name=name, agent_id=agent_id, payload=payload)
        self._tasks[task_id] = task
        self.logger.info("Submitted task %s for agent %s", task_id, agent_id)
        return task_id

    def get_task(self, task_id: str) -> Task:
        """Retrieve a previously submitted task."""
        return self._tasks[task_id]

    def run_task(self, task_id: str) -> ExecutionResult:
        """Execute the requested task and update its completion state."""
        task = self._tasks[task_id]
        task.mark_running()

        agent = self._agents.get(task.agent_id)
        if agent is None:
            task.mark_failed(f"Agent '{task.agent_id}' is not registered")
            return ExecutionResult(success=False, error=task.error, agent_id=task.agent_id)

        result = self.execution_engine.execute_agent(agent, task.payload)
        if result.success:
            task.mark_completed(result.output)
            self.shared_memory.set(f"task:{task.task_id}", result.output)
        else:
            task.mark_failed(result.error or "Agent execution failed")
        return result
