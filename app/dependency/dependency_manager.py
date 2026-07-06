"""Dependency tracking for AgentSphere OS agents and tasks."""

from __future__ import annotations

from typing import Any


class DependencyManager:
    """Maintains dependency relationships between agents and tasks."""

    def __init__(self) -> None:
        self._dependencies: dict[str, set[str]] = {}
        self._dependents: dict[str, set[str]] = {}

    def add_dependency(self, source: str, target: str) -> None:
        """Record that source depends on target."""
        self._dependencies.setdefault(source, set()).add(target)
        self._dependents.setdefault(target, set()).add(source)

    def get_dependencies(self, agent_id: str) -> set[str]:
        """Return direct dependencies for an agent."""
        return set(self._dependencies.get(agent_id, set()))

    def get_dependents(self, agent_id: str) -> set[str]:
        """Return agents that depend on the given agent."""
        return set(self._dependents.get(agent_id, set()))

    def get_affected_agents(self, failed_agent_id: str) -> set[str]:
        """Return all downstream agents affected by a failed agent."""
        affected: set[str] = set()
        queue = [failed_agent_id]
        while queue:
            current = queue.pop()
            for dependent in self.get_dependents(current):
                if dependent not in affected:
                    affected.add(dependent)
                    queue.append(dependent)
        return affected
