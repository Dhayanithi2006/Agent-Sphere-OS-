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

    def to_html(self) -> str:
        """Render an interactive HTML representation of the dependency graph using pyvis."""
        from pyvis.network import Network
        import json
        import re

        net = Network(notebook=False, directed=True, height="600px", width="100%", bgcolor="#0f172a", font_color="#f8fafc")
        
        options = {
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 3,
                "color": {
                    "border": "#3b82f6",
                    "background": "#1e293b",
                    "highlight": {
                        "border": "#60a5fa",
                        "background": "#334155"
                    },
                    "hover": {
                        "border": "#60a5fa",
                        "background": "#334155"
                    }
                },
                "font": {
                    "color": "#f8fafc",
                    "size": 15,
                    "face": "Outfit, Inter, system-ui, sans-serif"
                },
                "shape": "box",
                "margin": 12,
                "shadow": {
                    "enabled": True,
                    "color": "rgba(0,0,0,0.5)",
                    "size": 10,
                    "x": 0,
                    "y": 4
                }
            },
            "edges": {
                "arrows": {
                    "to": {
                        "enabled": True,
                        "scaleFactor": 1.1
                    }
                },
                "color": {
                    "color": "#475569",
                    "highlight": "#3b82f6",
                    "hover": "#3b82f6"
                },
                "smooth": {
                    "type": "cubicBezier",
                    "forceDirection": "horizontal",
                    "roundness": 0.5
                },
                "width": 2
            },
            "interaction": {
                "hover": True,
                "navigationButtons": True,
                "keyboard": True
            },
            "physics": {
                "hierarchicalRepulsion": {
                    "centralGravity": 0.0,
                    "springLength": 150,
                    "springConstant": 0.01,
                    "nodeDistance": 180,
                    "damping": 0.09
                },
                "solver": "hierarchicalRepulsion"
            }
        }
        
        net.set_options(json.dumps(options))

        for node in self.get_nodes():
            net.add_node(
                node, 
                label=node.upper(), 
                title=f"Agent: {node}\nStatus: Active Dependency Node", 
                shape="box"
            )
            
        for source, target in self.get_edges():
            net.add_edge(source, target)
            
        html = net.generate_html()
        
        font_link = '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">'
        
        premium_style = """
        <style type="text/css">
            body {
                margin: 0;
                padding: 24px;
                background-color: #090d16;
                font-family: 'Outfit', sans-serif;
                color: #f8fafc;
                display: flex;
                flex-direction: column;
                align-items: center;
                min-height: 100vh;
                box-sizing: border-box;
            }
            .header-container {
                max-width: 900px;
                width: 100%;
                margin-bottom: 24px;
                text-align: center;
            }
            h1 {
                font-size: 2.2rem;
                font-weight: 600;
                margin: 0 0 8px 0;
                background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p {
                color: #94a3b8;
                font-size: 1rem;
                margin: 0;
            }
            #mynetwork {
                max-width: 900px;
                width: 100%;
                height: 600px;
                background-color: #0f172a !important;
                border: 1px solid #1e293b;
                border-radius: 16px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
            }
        </style>
        """
        
        html = html.replace("<head>", f"<head>\n{font_link}")
        html = re.sub(r'<style type="text/css">.*?</style>', premium_style, html, flags=re.DOTALL)
        
        header_html = """
        <div class="header-container">
            <h1>AgentSphere OS</h1>
            <p>Interactive Agent Dependency Graph Runtime Model</p>
        </div>
        """
        html = html.replace("<body>", f"<body>\n{header_html}")
        
        return html
