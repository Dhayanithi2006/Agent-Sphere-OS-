"""Security manager for API key and agent access control."""

from __future__ import annotations

import os
from typing import Any


class SecurityManager:
    """Manages basic authorization checks for the AgentSphere API."""

    def __init__(self) -> None:
        allowed_api_keys = os.getenv("AGENTSPHERE_API_KEYS", "")
        allowed_agents = os.getenv("AGENTSPHERE_ALLOWED_AGENTS", "")
        self.allowed_api_keys = {key.strip() for key in allowed_api_keys.split(",") if key.strip()}
        self.allowed_agents = {agent.strip() for agent in allowed_agents.split(",") if agent.strip()}

    def authorize_api_key(self, api_key: str | None) -> bool:
        if not self.allowed_api_keys:
            return True
        return api_key is not None and api_key in self.allowed_api_keys

    def authorize_agent(self, agent_id: str) -> bool:
        if not self.allowed_agents:
            return True
        return agent_id in self.allowed_agents

    def is_secure(self) -> bool:
        return bool(self.allowed_api_keys or self.allowed_agents)

    def check_access(self, api_key: str | None, agent_id: str | None = None) -> bool:
        if not self.authorize_api_key(api_key):
            return False
        if agent_id is not None and not self.authorize_agent(agent_id):
            return False
        return True
