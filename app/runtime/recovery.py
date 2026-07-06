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

    def plan_recovery(self, failed_agent_id: str) -> list[str]:
        """Return the affected agents that should be re-executed."""
        return sorted(self.dependency_manager.get_affected_agents(failed_agent_id))

    def create_checkpoint(self, target_id: str, payload: dict[str, Any] | None = None) -> str:
        """Create and store a checkpoint for a target."""
        checkpoint = self.checkpoint_manager.save_checkpoint(target_id, payload)
        return checkpoint.checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore a checkpoint payload."""
        return self.checkpoint_manager.restore(checkpoint_id)
