"""Unit and integration tests for Module 2 (Microkernel & Process Manager)."""

from __future__ import annotations

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.models.process import Process, ProcessStatus
from app.runtime.process_repository import InMemoryProcessRepository
from app.runtime.process_manager import ProcessManager
from app.core.kernel import Microkernel
from main import app


@pytest.mark.anyio
async def test_process_repository_operations():
    """Verify InMemoryProcessRepository standard CRUD operations."""
    repo = InMemoryProcessRepository()
    
    # Verify empty list
    processes = await repo.list()
    assert len(processes) == 0

    # Add a process
    proc = Process(process_id="PID-9999", name="test-repo-agent")
    await repo.add(proc)
    
    # Retrieve process
    fetched = await repo.get("PID-9999")
    assert fetched is not None
    assert fetched.name == "test-repo-agent"
    assert fetched.status == ProcessStatus.CREATED

    # Update process
    fetched.status = ProcessStatus.RUNNING
    await repo.update(fetched)
    updated = await repo.get("PID-9999")
    assert updated.status == ProcessStatus.RUNNING

    # List processes
    all_procs = await repo.list()
    assert len(all_procs) == 1
    assert all_procs[0].process_id == "PID-9999"

    # Delete process
    deleted = await repo.delete("PID-9999")
    assert deleted is True
    assert await repo.get("PID-9999") is None


@pytest.mark.anyio
async def test_process_manager_lifecycle():
    """Verify ProcessManager PID allocation and state machine transitions."""
    repo = InMemoryProcessRepository()
    pm = ProcessManager(repo)

    # Test sequential PID allocation
    proc1 = await pm.create_process("agent-one")
    proc2 = await pm.create_process("agent-two")
    assert proc1.process_id == "PID-1001"
    assert proc2.process_id == "PID-1002"

    # Verify initial status
    assert proc1.status == ProcessStatus.CREATED

    # Suspend process (Valid: CREATED -> SUSPENDED)
    success = await pm.suspend_process(proc1.process_id)
    assert success is True
    assert await pm.get_process_status(proc1.process_id) == ProcessStatus.SUSPENDED

    # Suspend process again (Invalid: SUSPENDED -> SUSPENDED)
    success = await pm.suspend_process(proc1.process_id)
    assert success is False

    # Resume process (Valid: SUSPENDED -> RUNNING)
    success = await pm.resume_process(proc1.process_id)
    assert success is True
    assert await pm.get_process_status(proc1.process_id) == ProcessStatus.RUNNING

    # Resume process again (Invalid: RUNNING -> RUNNING)
    success = await pm.resume_process(proc1.process_id)
    assert success is False

    # Kill process (Valid: RUNNING -> KILLED)
    success = await pm.kill_process(proc1.process_id)
    assert success is True
    assert await pm.get_process_status(proc1.process_id) == ProcessStatus.KILLED

    # Kill process again (Invalid: KILLED -> KILLED)
    success = await pm.kill_process(proc1.process_id)
    assert success is False


@pytest.mark.anyio
async def test_microkernel_boot():
    """Verify Microkernel boots subsystems properly."""
    repo = InMemoryProcessRepository()
    pm = ProcessManager(repo)
    kernel = Microkernel(pm)
    
    assert kernel.is_booted is False
    await kernel.boot()
    assert kernel.is_booted is True


def test_process_apis():
    """Verify REST API process management endpoints."""
    with TestClient(app) as client:
        # 1. Create a process
        response = client.post("/kernel/processes", json={"name": "video-renderer", "metadata": {"task": "render"}})
        assert response.status_code == 201
        data = response.json()
        pid = data["process_id"]
        assert pid.startswith("PID-")
        assert data["name"] == "video-renderer"
        assert data["status"] == "created"
        assert data["metadata"]["task"] == "render"

        # 2. Get process status
        response = client.get(f"/kernel/processes/{pid}")
        assert response.status_code == 200
        assert response.json()["status"] == "created"

        # 3. List processes
        response = client.get("/kernel/processes")
        assert response.status_code == 200
        processes = response.json()
        assert len(processes) >= 1
        assert any(p["process_id"] == pid for p in processes)

        # 4. Suspend process
        response = client.post(f"/kernel/processes/{pid}/suspend")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        
        # Verify suspended status
        response = client.get(f"/kernel/processes/{pid}")
        assert response.json()["status"] == "suspended"

        # 5. Resume process
        response = client.post(f"/kernel/processes/{pid}/resume")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        
        # Verify running status
        response = client.get(f"/kernel/processes/{pid}")
        assert response.json()["status"] == "running"

        # 6. Kill process
        response = client.post(f"/kernel/processes/{pid}/kill")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify killed status
        response = client.get(f"/kernel/processes/{pid}")
        assert response.json()["status"] == "killed"

        # 7. Try invalid transition (resume a killed process)
        response = client.post(f"/kernel/processes/{pid}/resume")
        assert response.status_code == 400

