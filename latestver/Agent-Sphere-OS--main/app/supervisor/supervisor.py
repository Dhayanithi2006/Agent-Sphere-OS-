"""Supervisor engine that manages agent execution as OS-like processes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.logger import get_logger
from app.memory.shared_memory import SharedMemory
from app.models.agent_state import AgentState, AgentStatus
from app.models.process import Process, ProcessStatus
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
        self._agent_states: dict[str, AgentState] = {}
        self._processes: dict[str, Process] = {}
        self._task_to_process: dict[str, str] = {}
        self._pid_counter = 1
        self._is_running = False
        self.start_runtime()

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent so it can be used by the supervisor."""
        self._agents[agent.agent_id] = agent
        self._agent_states[agent.agent_id] = AgentState(agent_id=agent.agent_id)
        self.logger.info("Registered agent %s", agent.agent_id)

    def start_runtime(self) -> None:
        """Bring the supervisor runtime online."""
        self._is_running = True
        self.logger.info("Supervisor runtime started")

    def stop_runtime(self) -> None:
        """Pause the supervisor runtime."""
        self._is_running = False
        self.logger.info("Supervisor runtime stopped")

    def submit_task(self, name: str, agent_id: str, payload: dict[str, Any] | None = None) -> str:
        """Create and register a new task for execution."""
        task_id = str(uuid.uuid4())
        task = Task(task_id=task_id, name=name, agent_id=agent_id, payload=payload)
        self._tasks[task_id] = task
        self._create_process(task=task)
        self.logger.info("Submitted task %s for agent %s", task_id, agent_id)
        return task_id

    def assign_task(self, name: str, agent_id: str, payload: dict[str, Any] | None = None) -> str:
        """Assign a task to an agent and create a supervisory process entry."""
        self.logger.info("Assigning task %s to agent %s", name, agent_id)
        return self.submit_task(name=name, agent_id=agent_id, payload=payload)

    def get_task(self, task_id: str) -> Task:
        """Retrieve a previously submitted task."""
        return self._tasks[task_id]

    def get_agent_state(self, agent_id: str) -> AgentState:
        """Retrieve the managed state for an agent."""
        return self._agent_states[agent_id]

    def list_processes(self) -> list[dict[str, Any]]:
        """Return the current process table as serializable dictionaries."""
        return [self._serialize_process(process) for process in self._processes.values()]

    def get_supervisor_status(self) -> dict[str, Any]:
        """Return the supervisor's current runtime state."""
        return {
            "status": "running" if self._is_running else "stopped",
            "agent_count": len(self._agents),
            "task_count": len(self._tasks),
            "process_count": len(self._processes),
        }

    def _create_process(self, task: Task) -> Process:
        agent = self._agents.get(task.agent_id)
        agent_name = agent.name if agent is not None else task.agent_id
        process_id = self._next_pid()
        process = Process(
            process_id=process_id,
            name=task.name,
            status=ProcessStatus.CREATED,
            metadata={
                "agent_id": task.agent_id,
                "agent_name": agent_name,
                "task_id": task.task_id,
                "task_name": task.name,
            },
        )
        self._processes[process_id] = process
        self._task_to_process[task.task_id] = process_id
        state = self._agent_states.setdefault(task.agent_id, AgentState(agent_id=task.agent_id))
        state.metadata["active_task_id"] = task.task_id
        state.metadata["last_task_name"] = task.name
        state.metadata["last_updated_at"] = process.updated_at.isoformat()
        self.logger.info("Created process %s for task %s", process_id, task.task_id)
        return process

    def _next_pid(self) -> str:
        pid = f"pid-{self._pid_counter}"
        self._pid_counter += 1
        return pid

    def _update_process_state(self, task_id: str, state: ProcessStatus) -> None:
        process_id = self._task_to_process.get(task_id)
        if process_id is None:
            return
        process = self._processes[process_id]
        process.status = state
        process.updated_at = datetime.now(timezone.utc)
        process.metadata["updated_at"] = process.updated_at.isoformat()

    def _serialize_process(self, process: Process) -> dict[str, Any]:
        state = {
            ProcessStatus.CREATED: "READY",
            ProcessStatus.RUNNING: "RUNNING",
            ProcessStatus.STOPPED: "COMPLETED",
            ProcessStatus.FAILED: "FAILED",
        }[process.status]
        return {
            "pid": process.process_id,
            "agent": process.metadata.get("agent_id", process.name),
            "agent_name": process.metadata.get("agent_name", process.name),
            "state": state,
            "current_state": process.status.value,
            "current_task": process.metadata.get("task_name", process.name),
            "created_time": process.created_at.isoformat(),
            "updated_time": process.updated_at.isoformat(),
        }

    def run_task(self, task_id: str) -> ExecutionResult:
        """Execute the requested task and update its completion state."""
        task = self._tasks[task_id]
        task.mark_running()
        self._update_process_state(task_id, ProcessStatus.RUNNING)

        agent_state = self._agent_states.setdefault(task.agent_id, AgentState(agent_id=task.agent_id))
        agent_state.mark_running()

        agent = self._agents.get(task.agent_id)
        if agent is None:
            task.mark_failed(f"Agent '{task.agent_id}' is not registered")
            self._update_process_state(task_id, ProcessStatus.FAILED)
            agent_state.mark_failed(task.error)
            return ExecutionResult(success=False, error=task.error, agent_id=task.agent_id)

        result = self.execution_engine.execute_agent(agent, task.payload)
        if result.success:
            task.mark_completed(result.output)
            self.shared_memory.set(f"task:{task.task_id}", result.output)
            if isinstance(task.payload, dict):
                if "task" in task.payload:
                    self.shared_memory.write(namespace=task.agent_id, key="goal", value=str(task.payload["task"]))
                elif "goal" in task.payload:
                    self.shared_memory.write(namespace=task.agent_id, key="goal", value=task.payload["goal"])
                else:
                    self.shared_memory.write(namespace=task.agent_id, key="goal", value=task.name)
            else:
                self.shared_memory.write(namespace=task.agent_id, key="goal", value=task.name)
            self._update_process_state(task_id, ProcessStatus.STOPPED)
            agent_state.mark_completed()
        else:
            task.mark_failed(result.error or "Agent execution failed")
            self._update_process_state(task_id, ProcessStatus.FAILED)
            agent_state.mark_failed(task.error)
        return result
