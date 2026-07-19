"""Supervisor engine that coordinates agent executions as microkernel processes."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.core.logging import get_logger
from app.memory.shared_memory import SharedMemory
from app.models.agent_state import AgentState, AgentStatus
from app.models.process import Process, ProcessStatus
from app.models.task import Task, TaskStatus
from app.runtime.execution_engine import ExecutionEngine, ExecutionResult
from app.runtime.process_manager import ProcessManager

logger = get_logger("agentsphere.supervisor")


class Supervisor:
    """Coordinates task execution, lifecycle changes, retries, and process orchestration."""

    def __init__(
        self,
        process_manager: Optional[ProcessManager] = None,
        shared_memory: Optional[SharedMemory] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ) -> None:
        self.logger = logger
        if process_manager is None:
            try:
                from app.core.shared import process_manager as shared_pm
                process_manager = shared_pm
            except ImportError:
                from app.runtime.process_manager import ProcessManager
                from app.runtime.process_repository import InMemoryProcessRepository
                process_manager = ProcessManager(InMemoryProcessRepository())
        self.process_manager = process_manager

        self.shared_memory = shared_memory or SharedMemory()
        self.execution_engine = execution_engine or ExecutionEngine()
        self._agents: Dict[str, BaseAgent] = {}
        self._tasks: Dict[str, Task] = {}
        self._agent_states: Dict[str, AgentState] = {}
        self._task_to_process: Dict[str, str] = {}
        self._is_running = False
        self.start_runtime()

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent into the supervisor directory."""
        self._agents[agent.agent_id] = agent
        self._agent_states[agent.agent_id] = AgentState(agent_id=agent.agent_id)
        self.logger.info(f"Registered agent: {agent.agent_id}")

    def start_runtime(self) -> None:
        """Bring the supervisor manager online."""
        self._is_running = True
        self.logger.info("Supervisor runtime activated")

    def stop_runtime(self) -> None:
        """Bring the supervisor manager offline."""
        self._is_running = False
        self.logger.info("Supervisor runtime deactivated")

    async def submit_task(self, name: str, agent_id: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """Register a new task and spawn a corresponding microkernel process."""
        task_id = str(uuid.uuid4())
        task = Task(task_id=task_id, name=name, agent_id=agent_id, payload=payload)
        self._tasks[task_id] = task

        # Delegate process creation to the microkernel ProcessManager
        agent = self._agents.get(agent_id)
        agent_name = agent.name if agent else agent_id
        
        proc = await self.process_manager.create_process(
            name=name,
            metadata={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "task_id": task_id,
                "task_name": name,
            }
        )

        self._task_to_process[task_id] = proc.process_id

        # Initialize/update agent state
        state = self._agent_states.setdefault(agent_id, AgentState(agent_id=agent_id))
        state.metadata["active_task_id"] = task_id
        state.metadata["last_task_name"] = name
        state.metadata["last_updated_at"] = proc.updated_at.isoformat()

        self.logger.info(f"Submitted task '{task_id}' for agent '{agent_id}' under PID '{proc.process_id}'")
        return task_id

    async def assign_task(self, name: str, agent_id: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """Assign work to an agent, generating process registration."""
        self.logger.info(f"Assigning task '{name}' to agent '{agent_id}'")
        return await self.submit_task(name=name, agent_id=agent_id, payload=payload)

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task model by ID."""
        return self._tasks[task_id]

    def get_agent_state(self, agent_id: str) -> AgentState:
        """Retrieve the current tracking state of an agent."""
        return self._agent_states[agent_id]

    async def list_processes(self) -> List[Dict[str, Any]]:
        """Retrieve serializable process structures from the microkernel."""
        processes = await self.process_manager.list_processes()
        return [self._serialize_process(p) for p in processes]

    async def get_supervisor_status(self) -> Dict[str, Any]:
        """Fetch consolidated runtime metrics for the supervisor."""
        procs = await self.process_manager.list_processes()
        return {
            "status": "running" if self._is_running else "stopped",
            "agent_count": len(self._agents),
            "task_count": len(self._tasks),
            "process_count": len(procs),
        }

    def _serialize_process(self, process: Process) -> Dict[str, Any]:
        """Convert a Process dataclass to legacy status dictionaries."""
        state_mapping = {
            ProcessStatus.CREATED: "WAITING",
            ProcessStatus.RUNNING: "RUNNING",
            ProcessStatus.SUSPENDED: "SUSPENDED",
            ProcessStatus.STOPPED: "COMPLETED",
            ProcessStatus.FAILED: "FAILED",
            ProcessStatus.KILLED: "KILLED",
        }
        state_str = state_mapping.get(process.status, "UNKNOWN")
        return {
            "pid": process.process_id,
            "task_id": process.metadata.get("task_id"),
            "agent": process.metadata.get("agent_id", process.name),
            "agent_name": process.metadata.get("agent_name", process.name),
            "state": state_str,
            "current_state": process.status.value,
            "current_task": process.metadata.get("task_name", process.name),
            "created_time": process.created_at.isoformat(),
            "updated_time": process.updated_at.isoformat(),
        }

    async def run_task(self, task_id: str) -> ExecutionResult:
        """Execute the task asynchronously, transitioning process state with auto-retries on failure."""
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found")

        pid = self._task_to_process.get(task_id)
        if not pid:
            raise RuntimeError(f"No process registration found for task '{task_id}'")

        # Inject task metadata into task payload
        if task.payload is None:
            task.payload = {}
        task.payload["task_id"] = task_id
        task.payload["pid"] = pid

        agent = self._agents.get(task.agent_id)
        if not agent:
            error_msg = f"Agent '{task.agent_id}' is not registered"
            task.mark_failed(error_msg)
            await self.process_manager.fail_process(pid)
            agent_state = self._agent_states.setdefault(task.agent_id, AgentState(agent_id=task.agent_id))
            agent_state.mark_failed(error_msg)
            return ExecutionResult(success=False, error=error_msg, agent_id=task.agent_id)

        # Retrieve retry parameters from payload if provided
        max_retries = 3
        if isinstance(task.payload, dict):
            max_retries = int(task.payload.get("max_retries", max_retries))

        async def _run_via_scheduler():
            # 1. Update states to RUNNING
            task.mark_running()
            await self.process_manager.start_process(pid)

            agent_state = self._agent_states.setdefault(task.agent_id, AgentState(agent_id=task.agent_id))
            agent_state.mark_running()

            # 2. Asynchronous execution loop with retries
            result = None
            attempt = 0
            while attempt <= max_retries:
                try:
                    # Run synchronous execution logic in a thread pool to prevent blocking
                    result = await asyncio.to_thread(self.execution_engine.execute_agent, agent, task.payload)
                    if result.success:
                        break
                except Exception as exc:
                    result = ExecutionResult(success=False, error=str(exc), agent_id=task.agent_id)

                attempt += 1
                if attempt <= max_retries:
                    self.logger.warning(
                        f"Execution failed for task '{task_id}'. Retrying attempt {attempt}/{max_retries}...",
                        extra={"task_id": task_id, "error": result.error}
                    )
                    await asyncio.sleep(0.5)

            # 3. Post-execution status updates
            if result and result.success:
                task.mark_completed(result.output)
                self.shared_memory.set(f"task:{task.task_id}", result.output)

                # Standard goal metadata logging into shared memory namespace
                goal_value = task.name
                if isinstance(task.payload, dict):
                    goal_value = task.payload.get("task") or task.payload.get("goal") or task.name

                self.shared_memory.write(namespace=task.agent_id, key="goal", value=str(goal_value))
                await self.process_manager.complete_process(pid)
                agent_state.mark_completed()
            else:
                error_str = result.error if result else "Execution failed"
                task.mark_failed(error_str)
                await self.process_manager.fail_process(pid)
                agent_state.mark_failed(error_str)

            return result or ExecutionResult(success=False, error="Execution failed to run", agent_id=task.agent_id)

        # Execute using scheduler
        from app.core.shared import scheduler
        return await scheduler.execute_task(task_id, _run_via_scheduler, priority=0)
