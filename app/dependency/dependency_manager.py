"""Dependency tracking for AgentSphere OS agents and tasks."""

from __future__ import annotations

import networkx as nx
from typing import Any


class DependencyManager:
    """Maintains dependency relationships between agents and tasks."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def add_dependency(self, source: str, target: str) -> None:
        """Record that source depends on target."""
        self._graph.add_edge(source, target)

    def remove_dependency(self, source: str, target: str) -> None:
        """Remove a dependency edge between two nodes."""
        if self._graph.has_edge(source, target):
            self._graph.remove_edge(source, target)

    def get_dependencies(self, agent_id: str) -> set[str]:
        """Return direct dependencies for an agent."""
        return set(self._graph.successors(agent_id))

    def get_dependents(self, agent_id: str) -> set[str]:
        """Return agents that depend on the given agent."""
        return set(self._graph.predecessors(agent_id))

    def get_affected_agents(self, failed_agent_id: str) -> set[str]:
        """Return the agents downstream of a failure along the strongest dependency chain."""
        if not self._graph.has_node(failed_agent_id):
            return set()

        def walk(start: str, neighbor_fn: Any) -> set[str]:
            visited: set[str] = set()
            queue = list(neighbor_fn(start))
            while queue:
                current = queue.pop()
                if current in visited:
                    continue
                visited.add(current)
                queue.extend(neighbor_fn(current))
            return visited

        forward = walk(failed_agent_id, self._graph.successors)
        backward = walk(failed_agent_id, self._graph.predecessors)

        if len(forward) > len(backward):
            return forward
        if len(backward) > len(forward):
            return backward
        return forward or backward

    def traverse(self, start: str) -> list[str]:
        """Return a traversal order from the starting node."""
        if not self._graph.has_node(start):
            return []
        return list(nx.dfs_preorder_nodes(self._graph, start))

    def has_cycle(self) -> bool:
        """Return whether the dependency graph contains a cycle."""
        return nx.is_directed_acyclic_graph(self._graph) is False

    def to_dot(self) -> str:
        """Render a Graphviz-compatible dot representation of the graph."""
        try:
            import pydot  # type: ignore

            return nx.nx_pydot.to_pydot(self._graph).to_string()
        except ModuleNotFoundError:
            lines = ["digraph G {"]
            for node in sorted(self._graph.nodes()):
                lines.append(f'  "{node}";')
            for source, target in sorted(self._graph.edges()):
                lines.append(f'  "{source}" -> "{target}";')
            lines.append("}")
            return "\n".join(lines)

    def get_nodes(self) -> list[str]:
        """Return the current graph nodes."""
        return sorted(self._graph.nodes())

    def get_edges(self) -> list[tuple[str, str]]:
        """Return the current graph edges."""
        return sorted(self._graph.edges())
