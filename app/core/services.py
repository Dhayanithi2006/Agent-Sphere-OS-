"""Central runtime services and kernel components for AgentSphere OS."""

from __future__ import annotations

from app.core.config import settings
from app.core.logger import get_logger
from app.dependency.dependency_manager import DependencyManager
from app.events.event_bus import EventBus
from app.llm.model_router import ModelRouter
from app.memory.memory_manager import MemoryManager
from app.plugins.plugin_manager import PluginManager
from app.resources.resource_manager import ResourceManager
from app.security.security_manager import SecurityManager
from app.supervisor.supervisor import Supervisor
from app.tools.tool_registry import ToolRegistry


class RuntimeServices:
    """Shared services and singleton runtime components."""

    def __init__(self) -> None:
        self.settings = settings
        self.logger = get_logger("agentsphere.core.services")
        self.memory = MemoryManager()
        self.plugin_manager = PluginManager()
        self.tool_registry = ToolRegistry()
        self.security_manager = SecurityManager()
        self.dependency_manager = DependencyManager()
        self.event_bus = EventBus()
        self.resource_manager = ResourceManager()
        self.model_router = ModelRouter(default_provider=self.settings.default_model_provider)
        self.supervisor = Supervisor(shared_memory=self.memory, event_bus=self.event_bus)

        self._register_builtin_tools()
        self._register_builtin_agents()
        self._seed_default_dependency_graph()

    def _register_builtin_tools(self) -> None:
        builtins = [
            ("python", "Python Runtime", "Execute Python code in a sandboxed runtime."),
            ("git", "Git", "Inspect and manage project repositories."),
            ("filesystem", "Filesystem", "Read and write files on the host filesystem."),
            ("sql", "SQL", "Run SQL queries against connected databases."),
            ("browser", "Browser", "Browse public web pages and collect context."),
            ("search", "Search", "Perform search queries over external knowledge sources."),
            ("image", "Image Generation", "Generate or manipulate images using AI skills."),
            ("vision", "Vision", "Analyze images and extract visual insights."),
            ("audio", "Audio", "Process or generate speech and audio content."),
            ("video", "Video", "Create or analyze video content using AI skills."),
        ]
        for tool_id, name, description in builtins:
            self.tool_registry.register_tool(tool_id, name, description, metadata={"builtin": True})

    def _register_builtin_agents(self) -> None:
        from app.agents.developer import DeveloperAgent
        from app.agents.planner import PlannerAgent
        from app.agents.researcher import ResearcherAgent
        from app.agents.reviewer import ReviewerAgent
        from app.agents.tester import TesterAgent

        builtin_agents = {
            "planner": PlannerAgent,
            "researcher": ResearcherAgent,
            "developer": DeveloperAgent,
            "tester": TesterAgent,
            "reviewer": ReviewerAgent,
        }

        for agent_id, agent_cls in builtin_agents.items():
            self.plugin_manager.register_agent_factory(agent_id, agent_cls, metadata={"builtin": True})
            self.supervisor.register_agent(agent_cls(model_router=self.model_router))

    def _seed_default_dependency_graph(self) -> None:
        dependency_pairs = [
            ("planner", "researcher"),
            ("researcher", "developer"),
            ("developer", "tester"),
            ("tester", "reviewer"),
        ]
        for source, target in dependency_pairs:
            self.dependency_manager.add_dependency(source, target)

    def list_registered_agents(self) -> list[str]:
        return sorted(self.supervisor._agents.keys())

    def list_available_plugins(self) -> list[str]:
        return sorted(self.plugin_manager.list_agents())


runtime = RuntimeServices()
