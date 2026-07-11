"""Tool registry for AgentSphere OS shared operating system services."""

from __future__ import annotations

from typing import Any


class ToolRegistry:
    """Registry of tools available to agents and the runtime."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register_tool(self, tool_id: str, name: str, description: str, metadata: dict[str, Any] | None = None) -> None:
        self._tools[tool_id] = {
            "id": tool_id,
            "name": name,
            "description": description,
            "metadata": metadata or {},
        }

    def get_tool(self, tool_id: str) -> dict[str, Any] | None:
        return self._tools.get(tool_id)

    def list_tools(self) -> list[dict[str, Any]]:
        return list(self._tools.values())
