"""Agent marketplace for loading plugins that extend the kernel."""

from __future__ import annotations

import importlib
from typing import Any, Callable

from app.agents.base_agent import BaseAgent


class PluginManager:
    """A simple plugin registry for extending AgentSphere OS."""

    def __init__(self) -> None:
        self._agent_factories: dict[str, Callable[..., BaseAgent]] = {}
        self._plugin_metadata: dict[str, dict[str, Any]] = {}

    def register_agent_factory(self, agent_id: str, factory: Callable[..., BaseAgent], metadata: dict[str, Any] | None = None) -> None:
        self._agent_factories[agent_id] = factory
        self._plugin_metadata[agent_id] = metadata or {"source": "builtin"}

    def get_agent_factory(self, agent_id: str) -> Callable[..., BaseAgent] | None:
        return self._agent_factories.get(agent_id)

    def create_agent(self, agent_id: str, **kwargs: Any) -> BaseAgent:
        factory = self.get_agent_factory(agent_id)
        if factory is None:
            raise KeyError(f"Plugin agent '{agent_id}' is not registered")
        return factory(**kwargs)

    def list_agents(self) -> list[str]:
        return sorted(self._agent_factories.keys())

    def load_agent_plugin(self, module_path: str, class_name: str, agent_id: str, metadata: dict[str, Any] | None = None) -> None:
        module = importlib.import_module(module_path)
        agent_class = getattr(module, class_name)
        if not issubclass(agent_class, BaseAgent):
            raise TypeError("Loaded plugin class must inherit from BaseAgent")
        self.register_agent_factory(agent_id, agent_class, metadata=metadata)
