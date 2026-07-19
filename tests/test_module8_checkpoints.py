"""Unit and integration tests for Module 8 (Checkpoint Manager)."""

from __future__ import annotations

import time
import pytest
from app.checkpoint.checkpoint_manager import CheckpointManager


@pytest.fixture
def test_manager() -> CheckpointManager:
    """Fixture providing an isolated in-memory SQLite CheckpointManager."""
    return CheckpointManager(db_path=":memory:")


def test_checkpoint_store_and_restore(test_manager):
    """Verify that state snapshots can be persisted and restored."""
    manager = test_manager
    state = {"stage": "init", "files_created": ["main.py"]}

    # Create checkpoint
    cp = manager.create_checkpoint(task_id="task_123", name="initial_setup", state=state)
    assert cp.id.startswith("cp-task_123-")
    assert cp.name == "initial_setup"
    assert cp.state == state

    # Fetch checkpoint
    fetched = manager.get_checkpoint(cp.id)
    assert fetched is not None
    assert fetched.id == cp.id
    assert fetched.state == state

    # Restore state
    restored = manager.restore(cp.id)
    assert restored == state


def test_checkpoint_version_logs(test_manager):
    """Verify that multiple checkpoints are versioned chronologically."""
    manager = test_manager

    # Save multiple checkpoints
    cp1 = manager.save_checkpoint("agent_a", {"stage": "start"})
    time.sleep(0.01) # Ensure distinct timestamp IDs
    cp2 = manager.save_checkpoint("agent_a", {"stage": "running"})
    time.sleep(0.01)
    cp3 = manager.save_checkpoint("agent_a", {"stage": "finished"})

    # Check version history
    versions = manager.get_versions("agent_a")
    assert len(versions) == 3
    assert versions[0] == cp1.id
    assert versions[1] == cp2.id
    assert versions[2] == cp3.id

    # Check latest retrieval
    latest = manager.get_latest("agent_a")
    assert latest is not None
    assert latest.id == cp3.id
    assert latest.state["stage"] == "finished"


def test_transactional_rollback_pruning(test_manager):
    """Verify rolling back to a checkpoint prunes all checkpoints created after it."""
    manager = test_manager

    # Save three versions of a task
    cp1 = manager.save_checkpoint("agent_b", {"val": 10})
    time.sleep(0.01)
    cp2 = manager.save_checkpoint("agent_b", {"val": 20})
    time.sleep(0.01)
    cp3 = manager.save_checkpoint("agent_b", {"val": 30})

    # Assert all three exist
    assert len(manager.get_versions("agent_b")) == 3

    # Rollback to checkpoint 1 (val: 10)
    restored_state = manager.rollback_to_checkpoint(cp1.id)
    assert restored_state == {"val": 10}

    # Verify newer checkpoints (cp2 and cp3) have been pruned from database
    remaining_versions = manager.get_versions("agent_b")
    assert len(remaining_versions) == 1
    assert remaining_versions[0] == cp1.id

    # Assert get_latest now returns checkpoint 1
    latest = manager.get_latest("agent_b")
    assert latest is not None
    assert latest.id == cp1.id
    assert latest.state == {"val": 10}
