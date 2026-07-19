"""Unit and integration tests for Module 5 (Hybrid Shared Memory)."""

from __future__ import annotations

import asyncio
import pytest

from app.core.config import AppSettings
from app.memory.memory_manager import MemoryManager


@pytest.fixture
def test_memory() -> MemoryManager:
    """Fixture providing an isolated in-memory SQLite MemoryManager instance."""
    return MemoryManager(db_path=":memory:")


@pytest.mark.anyio
async def test_memory_transactions(test_memory):
    """Verify transactional boundaries, buffered writes, commits, and rollbacks."""
    mem = test_memory

    # Initial write path
    mem.write(namespace="agent_a", key="status", value="idle")
    assert mem.read("agent_a", "status") == "idle"

    # Start a transaction
    tx_id = mem.begin_transaction()
    
    # Write under transaction
    mem.write(namespace="agent_a", key="status", value="running", tx_id=tx_id)
    mem.write(namespace="agent_a", key="progress", value=50, tx_id=tx_id)

    # Verify standard reads do NOT see transaction changes yet
    assert mem.read("agent_a", "status") == "idle"
    assert mem.read("agent_a", "progress") is None

    # Commit transaction
    mem.commit_transaction(tx_id)

    # Verify changes are committed
    assert mem.read("agent_a", "status") == "running"
    assert mem.read("agent_a", "progress") == 50

    # Start a new transaction to test rollback
    tx_id_2 = mem.begin_transaction()
    mem.write(namespace="agent_a", key="status", value="completed", tx_id=tx_id_2)
    mem.rollback_transaction(tx_id_2)

    # Verify value did NOT change after rollback
    assert mem.read("agent_a", "status") == "running"


@pytest.mark.anyio
async def test_memory_locking(test_memory):
    """Verify lease-based locking exclusion limits."""
    mem = test_memory
    lock_key = "process:resource:123"

    # Acquire lock for Owner A for 1 second lease
    acquired = await mem.acquire_lock(lock_key, owner_id="owner_a", lease_duration_seconds=1.0)
    assert acquired is True

    # Owner B tries to acquire lock and fails
    acquired_b = await mem.acquire_lock(lock_key, owner_id="owner_b", lease_duration_seconds=1.0)
    assert acquired_b is False

    # Owner A releases the lock
    released = await mem.release_lock(lock_key, owner_id="owner_a")
    assert released is True

    # Owner B can now acquire the lock
    acquired_b_new = await mem.acquire_lock(lock_key, owner_id="owner_b", lease_duration_seconds=1.0)
    assert acquired_b_new is True

    # Wait for Owner B's lock lease to expire (1.1s)
    await asyncio.sleep(1.1)

    # Owner A can now acquire it due to lease expiration
    acquired_a_after_expiry = await mem.acquire_lock(lock_key, owner_id="owner_a", lease_duration_seconds=1.0)
    assert acquired_a_after_expiry is True


@pytest.mark.anyio
async def test_vector_memory_similarity_search(test_memory):
    """Verify deterministic vector generation and cosine similarity lookup queries."""
    mem = test_memory

    # Add text entries into vector memory
    await mem.add_vector("Generate advertisement copy for Wan Video agent workflows", {"domain": "video"})
    await mem.add_vector("Build test suite for the FastAPI microkernel bootstrap layer", {"domain": "tests"})
    await mem.add_vector("Draft reviewer comments for publishing", {"domain": "reviews"})

    # Query for "FastAPI microkernel"
    results = await mem.query_vector("FastAPI microkernel", top_k=2)

    assert len(results) >= 1
    # The highest scoring similarity must be the FastAPI microkernel string
    assert "FastAPI microkernel" in results[0]["text"]
    assert results[0]["metadata"]["domain"] == "tests"
    assert results[0]["similarity"] > 0.0


@pytest.mark.anyio
async def test_versioning_rollback_history(test_memory):
    """Verify that updating keys tracks version history and rollback updates state."""
    mem = test_memory
    key = "counter"

    mem.write(namespace=None, key=key, value=10)
    mem.write(namespace=None, key=key, value=20)
    mem.write(namespace=None, key=key, value=30)

    # Verify history
    h = mem.history(namespace=None, key=key)
    assert len(h) == 3
    assert h[0]["version"] == 1
    assert h[0]["value"] == 10
    assert h[1]["version"] == 2
    assert h[1]["value"] == 20
    assert h[2]["version"] == 3
    assert h[2]["value"] == 30

    # Rollback to version 1
    success = mem.rollback_key_to_version(namespace=None, key=key, version=1)
    assert success is True

    # Current value should be 10 (rolled back)
    assert mem.read(namespace=None, key=key) == 10


@pytest.mark.anyio
async def test_memory_snapshot_restore(test_memory):
    """Verify snapshot dumps and state restores correctly overwrite tables."""
    mem = test_memory

    mem.write(namespace="ns1", key="a", value={"val": 1})
    mem.write(namespace="ns2", key="b", value={"val": 2})

    # Create snapshot
    snapshot_json = mem.create_snapshot()
    
    # Delete active keys
    mem.delete(namespace="ns1", key="a")
    mem.delete(namespace="ns2", key="b")

    assert mem.read("ns1", "a") is None

    # Restore snapshot
    mem.restore_snapshot(snapshot_json)

    # Assert values restored
    assert mem.read("ns1", "a") == {"val": 1}
    assert mem.read("ns2", "b") == {"val": 2}
