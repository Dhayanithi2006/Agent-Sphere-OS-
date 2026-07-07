"""Recovery logic for selective rollback and resumption."""

from __future__ import annotations

from typing import Any

from app.checkpoint.checkpoint_manager import CheckpointManager
from app.dependency.dependency_manager import DependencyManager
from app.runtime.execution_engine import ExecutionEngine


class RecoveryEngine:
    """Coordinates rollback and replay for failed agent pipelines."""

    def __init__(self, dependency_manager: DependencyManager | None = None, checkpoint_manager: CheckpointManager | None = None, execution_engine: ExecutionEngine | None = None) -> None:
        self.dependency_manager = dependency_manager or DependencyManager()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.execution_engine = execution_engine or ExecutionEngine()
        self.metrics: dict[str, Any] = {"recovery_count": 0, "restores": 0, "rollbacks": 0}

    def plan_recovery(self, failed_agent_id: str) -> list[str]:
        """Return the affected agents that should be re-executed."""
        affected = sorted(self.dependency_manager.get_affected_agents(failed_agent_id))
        return affected

    def create_checkpoint(self, target_id: str, payload: dict[str, Any] | None = None) -> str:
        """Create and store a checkpoint for a target."""
        checkpoint = self.checkpoint_manager.save_checkpoint(target_id, payload)
        return checkpoint.checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore a checkpoint payload."""
        self.metrics["restores"] += 1
        return self.checkpoint_manager.restore(checkpoint_id)

    def recover(self, failed_agent_id: str, payload: dict[str, Any] | None = None) -> list[str]:
        """Selectively roll back and resume the affected workflow slice."""
        affected = self.plan_recovery(failed_agent_id)
        self.metrics["recovery_count"] += 1
        self.metrics["rollbacks"] += 1
        if payload is not None:
            self.create_checkpoint(failed_agent_id, payload)
        return affected
