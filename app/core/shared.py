"""Centralized singleton registry for core AgentSphere OS v4 subsystems."""

from __future__ import annotations

from app.runtime.process_repository import InMemoryProcessRepository
from app.runtime.process_manager import ProcessManager
from app.core.kernel import Microkernel
from app.supervisor.supervisor import Supervisor
from app.events.event_bus import EventBus
from app.runtime.scheduler import Scheduler
from app.dependency.dependency_manager import DependencyManager
from app.checkpoint.checkpoint_manager import CheckpointManager
from app.runtime.recovery import RecoveryEngine
from app.llm.model_router import ModelRouter
from app.resources.resource_manager import ResourceManager
from app.plugins.plugin_manager import PluginManager
from app.tools.tool_registry import ToolRegistry
from app.runtime.execution_engine import ExecutionEngine
from app.security.sandbox import ProcessSandbox
from app.memory.shared_memory import SharedMemory
from app.tools.tool_manager import ToolManager


# Singletons shared across bootstrap lifespan and API router layers
process_repository = InMemoryProcessRepository()
process_manager = ProcessManager(process_repository)
kernel = Microkernel(process_manager)
event_bus = EventBus()
scheduler = Scheduler()
dependency_manager = DependencyManager()
checkpoint_manager = CheckpointManager()
recovery_engine = RecoveryEngine()
model_router = ModelRouter()
resource_manager = ResourceManager()
plugin_manager = PluginManager()
tool_registry = ToolRegistry()
tool_manager = ToolManager(tool_registry)
execution_engine = ExecutionEngine()
process_sandbox = ProcessSandbox()
shared_memory = SharedMemory()
supervisor = Supervisor(process_manager=process_manager)


