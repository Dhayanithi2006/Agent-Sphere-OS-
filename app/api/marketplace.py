"""Marketplace Manager: Handles hot-loading and installing external plugins dynamically."""

from __future__ import annotations

from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.core.shared import supervisor
from app.core.logger import get_logger

logger = get_logger("agentsphere.marketplace")


class MarketplaceAgent(BaseAgent):
    """Mock agent registered dynamically from the plugin store without kernel reboot."""

    def __init__(self, agent_id: str, name: str, description: str) -> None:
        super().__init__(agent_id=agent_id, name=name, description=description)

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info(f"Marketplace Agent '{self.agent_id}' running.")
        return f"Marketplace Agent '{self.name}' processed operations successfully."


class MarketplaceManager:
    """Orchestrates mock third-party plugin downloads, installation and dynamic registration."""

    CATALOG = {
        "marketing_agent": {"name": "Marketing Agent", "desc": "Audits SEO hooks and drafts social copies."},
        "music_agent": {"name": "Music Composer Agent", "desc": "Generates ambient synth pads and tracks."},
        "finance_agent": {"name": "Finance Audit Agent", "desc": "Monitors platform licensing and billing records."},
        "translation_agent": {"name": "Translation Agent", "desc": "Translates subtitle transcripts into 40+ language schemas."}
    }

    @classmethod
    def list_catalog(cls) -> List[Dict[str, str]]:
        """List all available plugins in store."""
        return [{"id": k, "name": v["name"], "desc": v["desc"]} for k, v in cls.CATALOG.items()]

    @classmethod
    def install_plugin(cls, plugin_id: str) -> bool:
        """Dynamically instantiate and hot-load the plugin into the running supervisor."""
        if plugin_id not in cls.CATALOG:
            logger.warning(f"Plugin '{plugin_id}' not found in marketplace catalog.")
            return False

        info = cls.CATALOG[plugin_id]
        agent = MarketplaceAgent(agent_id=plugin_id, name=info["name"], description=info["desc"])
        supervisor.register_agent(agent)
        logger.info(f"Marketplace: Dynamically hot-loaded agent '{plugin_id}' into supervisor.")
        return True
