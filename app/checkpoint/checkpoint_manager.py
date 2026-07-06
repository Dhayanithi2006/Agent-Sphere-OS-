"""Checkpoint manager for restoring agent state after failures."""

from __future__ import annotations

from typing import Any

from app.models.checkpoint import Checkpoint


class CheckpointManager:
    """Stores snapshots of agent or task state for recovery workflows."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}

    def save_checkpoint(self, target_id: str, payload: dict[str, Any] | None = None) -> Checkpoint:
        """Persist a checkpoint for a target identifier."""
        checkpoint = Checkpoint(checkpoint_id=f"cp-{target_id}", target_id=target_id, payload=payload or {})
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Retrieve a previously saved checkpoint."""
        return self._checkpoints.get(checkpoint_id)

    def restore(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore payload from a checkpoint."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint is None:
            raise KeyError(f"Checkpoint {checkpoint_id} was not found")
        return checkpoint.payload
