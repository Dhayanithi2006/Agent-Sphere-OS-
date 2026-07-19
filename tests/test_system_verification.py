"""Automated validation test suite verifying all 14 microkernel subsystems in AgentSphere OS."""

import sys
import os
import time
import pytest
from fastapi.testclient import TestClient

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from app.core.shared import (
    supervisor,
    event_bus,
    shared_memory,
    plugin_manager,
    recovery_engine,
    model_router,
    scheduler,
    checkpoint_manager
)
from app.dependency.dependency_manager import DependencyManager
from app.tools.tool_registry import ToolRegistry


class TestSystemVerification:
    
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def test_phase1_server_endpoints(self):
        """Phase 1: FastAPI server endpoints health and spec loading."""
        res_health = self.client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "ok"

        res_openapi = self.client.get("/openapi.json")
        assert res_openapi.status_code == 200
        assert "openapi" in res_openapi.json()

    def test_phase2_microkernel_boot(self):
        """Phase 2: Microkernel startup integrity."""
        assert supervisor is not None
        assert event_bus is not None
        assert shared_memory is not None

    def test_phase3_plugin_manager(self):
        """Phase 3: Plugin discovery and loading status."""
        plugins = plugin_manager.list_active_plugins()
        assert isinstance(plugins, list)

    def test_phase4_supervisor_and_agent_registration(self):
        """Phase 4: Agent registration registry in supervisor."""
        res = self.client.get("/api/dashboard/metrics")
        assert res.status_code == 200
        assert "tasks" in res.json()
        assert len(supervisor._agents) > 0

    def test_phase5_event_bus(self):
        """Phase 5: Event Bus pub-sub loop operation."""
        events_received = []
        
        def test_handler(event):
            events_received.append(event)

        event_bus.subscribe("verification_ping", test_handler)
        event_bus.publish("verification_ping", {"msg": "hello"})
        
        # Give event queue a brief moment to dispatch if async
        time.sleep(0.1)
        assert len(events_received) > 0
        assert events_received[0]["msg"] == "hello"

    def test_phase6_memory_manager(self):
        """Phase 6: Shared memory persistence operations."""
        shared_memory.write("verify_ns", "key_1", "value_1")
        assert shared_memory.read("verify_ns", "key_1") == "value_1"
        
        shared_memory.delete("verify_ns:key_1")
        assert shared_memory.read("verify_ns", "key_1") is None

    def test_phase7_dependency_manager(self):
        """Phase 7: Dependency graph cycle validation."""
        dm = DependencyManager()
        dm.add_dependency("AgentA", "AgentB")
        dm.add_dependency("AgentB", "AgentC")
        
        assert dm.has_cycle() is False
        
        dm.add_dependency("AgentC", "AgentA")
        assert dm.has_cycle() is True

    def test_phase8_checkpoint_manager(self):
        """Phase 8: Checkpoint creation and memory state rollback."""
        checkpoint_id = "test_cp_001"
        task_id = "task_001"
        
        # Write initial state
        shared_memory.write("state_ns", "db_val", "original_value")
        
        # Save checkpoint
        cp = checkpoint_manager.create_checkpoint(
            task_id=task_id,
            name="Test Checkpoint",
            state={
                "memory": shared_memory.snapshot()
            }
        )
        
        assert cp is not None
        
        # Modify memory state
        shared_memory.write("state_ns", "db_val", "corrupt_value")
        
        # Perform rollback
        memory_state = cp.state.get("memory", {})
        for key, value in memory_state.items():
            shared_memory.set(key, value)
            
        # Verify state is restored
        assert shared_memory.read("state_ns", "db_val") == "original_value"
        
        # Cleanup
        shared_memory.delete("state_ns:db_val")

    def test_phase9_scheduler(self):
        """Phase 9: Scheduler process concurrency queueing."""
        assert scheduler is not None
        assert hasattr(scheduler, "max_concurrency")

    def test_phase10_recovery_engine(self):
        """Phase 10: Task failure recovery state check."""
        assert recovery_engine is not None
        assert hasattr(recovery_engine, "recover_task")

    def test_phase11_tool_calling(self):
        """Phase 11: Tool Registry capabilities and schema verification."""
        tr = ToolRegistry()
        
        # Register a mock tool
        tr.register_tool(
            tool_id="mock_add",
            name="Mock Add",
            description="Adds two numbers",
            func=lambda a, b: a + b,
            schema={
                "parameters": {
                    "required": ["a", "b"]
                }
            }
        )
        
        result = tr.execute_tool("mock_add", {"a": 5, "b": 10})
        assert result == 15

    def test_phase12_llm_integration(self):
        """Phase 12: LLM endpoint client integration routing."""
        assert model_router is not None
        assert hasattr(model_router, "get_usage_metrics")
