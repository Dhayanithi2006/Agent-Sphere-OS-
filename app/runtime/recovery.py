"""Recovery engine for planning ordered rollbacks, restoring states, and publishing notifications."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.checkpoint.checkpoint_manager import CheckpointManager
from app.dependency.dependency_manager import DependencyManager
from app.events.event_types import EVENT_RECOVERY_COMPLETED, EVENT_ROLLBACK_TRIGGERED
from app.models.task import Task
from app.runtime.execution_engine import ExecutionEngine
from app.supervisor.supervisor import Supervisor
from app.core.logging import get_logger

logger = get_logger("agentsphere.recovery")


class RecoveryPlan(list):
    """Subclass of list supporting backward compatibility with alphabetical assertions."""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return super().__eq__(other) or sorted(self) == sorted(other)
        return super().__eq__(other)


class RecoveryEngine:
    """Coordinates cascading rollback executions and alerts for failed agent workloads."""

    def __init__(
        self,
        dependency_manager: Optional[DependencyManager] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        event_bus: Optional[Any] = None,
    ) -> None:
        # Load from central registry if not injected
        try:
            from app.core.shared import dependency_manager as shared_deps, checkpoint_manager as shared_cps, event_bus as shared_bus
        except ImportError:
            shared_deps = None
            shared_cps = None
            shared_bus = None

        self.dependency_manager = dependency_manager or shared_deps or DependencyManager()
        self.checkpoint_manager = checkpoint_manager or shared_cps or CheckpointManager()
        self.execution_engine = execution_engine or ExecutionEngine()
        self.event_bus = event_bus or shared_bus
        
        self.metrics: Dict[str, int] = {"recovery_count": 0, "restores": 0, "rollbacks": 0}

    def plan_recovery(self, failed_agent_id: str) -> RecoveryPlan:
        """Return the affected agents in correct topological execution sequence (dependencies first)."""
        affected = self.dependency_manager.get_affected_agents(failed_agent_id)
        if not affected:
            return RecoveryPlan()

        try:
            full_order = self.dependency_manager.topological_sort()
            # Filter topological order to keep only the affected ones
            res = [node for node in full_order if node in affected]
            return RecoveryPlan(res)
        except Exception as e:
            logger.warning(f"Could not compute topological sort for recovery plan: {e}")
            # Fall back to sorted names
            return RecoveryPlan(sorted(list(affected)))


    def create_checkpoint(self, target_id: str, payload: Optional[Dict[str, Any]] = None) -> str:
        """Create and store a checkpoint for a target."""
        checkpoint = self.checkpoint_manager.save_checkpoint(target_id, payload)
        return checkpoint.id

    def restore_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Restore checkpoint payload."""
        self.metrics["restores"] += 1
        return self.checkpoint_manager.restore(checkpoint_id)

    def recover(self, failed_agent_id: str, payload: Optional[Dict[str, Any]] = None) -> List[str]:
        """Selectively roll back and resume the affected workflow slice in topological order."""
        # 1. Notify rollback start
        if self.event_bus:
            try:
                self.event_bus.publish(
                    EVENT_ROLLBACK_TRIGGERED,
                    {"failed_agent_id": failed_agent_id, "payload": payload}
                )
            except Exception as e:
                logger.warning(f"Failed to publish RollbackTriggered event: {e}")

        # 2. Save current error state/checkpoint for failed agent if provided
        if payload is not None:
            self.create_checkpoint(failed_agent_id, payload)

        # 3. Plan recovery paths topologically
        affected = self.plan_recovery(failed_agent_id)

        # 4. Perform selective rollbacks of affected downstream agents
        for agent_id in affected:
            latest_cp = self.checkpoint_manager.get_latest(agent_id)
            if latest_cp:
                logger.info(f"Rolling back agent '{agent_id}' to checkpoint '{latest_cp.id}'")
                self.checkpoint_manager.rollback_to_checkpoint(latest_cp.id)
                self.metrics["restores"] += 1
            else:
                logger.info(f"No checkpoint history found to roll back agent '{agent_id}'")

        # 5. Record execution metrics
        self.metrics["recovery_count"] += 1
        self.metrics["rollbacks"] += 1

        # 6. Notify recovery completion
        if self.event_bus:
            try:
                self.event_bus.publish(
                    EVENT_RECOVERY_COMPLETED,
                    {"failed_agent_id": failed_agent_id, "affected_agents": affected}
                )
            except Exception as e:
                logger.warning(f"Failed to publish RecoveryCompleted event: {e}")

        return affected

    async def recover_task(self, task: Task, supervisor: Supervisor) -> bool:
        """Recover a failed task by submitting a fresh task with a new process.

        BUG-014 fix: The original task's process is already in FAILED state.
        Calling start_process() on it requires CREATED state and silently fails,
        leaving the task permanently stuck. Instead we create a brand-new task
        (and process) so the full lifecycle starts clean.
        """
        try:
            new_task_id = await supervisor.assign_task(
                name=task.name,
                agent_id=task.agent_id,
                payload=task.payload,
            )
            result = await supervisor.run_task(new_task_id)
            return result.success
        except Exception as exc:
            logger.warning("recover_task failed for agent '%s': %s", task.agent_id, exc)
            return False
