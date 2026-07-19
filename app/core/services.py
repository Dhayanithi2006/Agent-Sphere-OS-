"""Central runtime services and kernel components for AgentSphere OS."""

from __future__ import annotations

from app.core.config import settings
from app.core.logger import get_logger


class RuntimeServices:
    """Shared services and singleton runtime components.

    Note: All heavy singletons (kernel, supervisor, model_router, etc.) are
    owned by app.core.shared.  This class only wires up the builtin coding
    agents into that shared supervisor so they are available from the start.
    """

    def __init__(self) -> None:
        self.settings = settings
        self.logger = get_logger("agentsphere.core.services")
        self._register_builtin_agents()

    def _register_builtin_agents(self) -> None:
        """Register the five builtin coding agents into the shared supervisor."""
        try:
            from app.core.shared import supervisor, model_router, plugin_manager
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
                # Skip if already registered (prevents duplicate registration on reload)
                if agent_id not in supervisor._agents:
                    agent = agent_cls(model_router=model_router)
                    plugin_manager.register_agent_factory(agent_id, agent_cls, metadata={"builtin": True})
                    supervisor.register_agent(agent)
                    self.logger.info(f"Registered builtin agent: {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to register builtin agents: {e}", exc_info=True)

    def list_registered_agents(self) -> list[str]:
        from app.core.shared import supervisor
        return sorted(supervisor._agents.keys())


runtime = RuntimeServices()
