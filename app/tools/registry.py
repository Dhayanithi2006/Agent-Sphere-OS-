"""Unified Tool Registry: System calls table for agent tool execution."""

from __future__ import annotations

from typing import Any, Callable, Dict
from app.core.logger import get_logger

logger = get_logger("agentsphere.tools.registry")


class ToolRegistry:
    """Manages available sandbox and cloud integrations through a single registry console."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._init_default_tools()

    def register_tool(self, name: str, func: Callable[..., Any]) -> None:
        """Register a tool callback."""
        self._tools[name] = func
        logger.info(f"Registered tool in registry: {name}")

    def execute_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a registered tool by name with arguments."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in ToolRegistry.")
        import time
        print("=" * 60)
        print(f"TOOL INVOKED : {name}")
        print(f"ARGUMENTS    : args={args}, kwargs={kwargs}")
        start = time.time()
        logger.info(f"Executing tool '{name}' (args: {args}, kwargs: {kwargs})")
        try:
            res = self._tools[name](*args, **kwargs)
            print("STATUS       : SUCCESS")
            print(f"DURATION     : {time.time() - start:.2f}s")
            print("=" * 60)
            return res
        except Exception as e:
            print("STATUS       : FAILED")
            print(f"DURATION     : {time.time() - start:.2f}s")
            print("=" * 60)
            logger.error(f"Failed to execute tool '{name}': {e}")
            return f"Error executing tool '{name}': {e}"

    def list_tools(self) -> list[str]:
        """List names of all registered tools."""
        return list(self._tools.keys())

    def _init_default_tools(self) -> None:
        # Register standard developer and collaboration workflows
        self.register_tool("browser_search", lambda q: f"Browser search results for '{q}': [1] 'Official Guide', [2] 'Best Practices'")
        self.register_tool("git_commit", lambda msg: f"Git: committed changes with message '{msg}'")
        self.register_tool("python_sandbox", lambda code: f"Python Sandbox: executed script successfully. Output: success.")
        self.register_tool("youtube_upload", lambda f: f"YouTube: uploaded movie clip '{f}' to channel.")
        self.register_tool("drive_sync", lambda f: f"Google Drive: synced file '{f}' to cloud storage.")
        self.register_tool("alibaba_oss_upload", lambda s, d: f"Alibaba OSS: uploaded source '{s}' to target object '{d}'.")
        self.register_tool("email_send", lambda to, s, m: f"Email: sent message to '{to}' with subject '{s}'.")
        self.register_tool("slack_notify", lambda msg: f"Slack: broadcast notification message '{msg}'.")
        self.register_tool("github_create_pr", lambda repo, title: f"GitHub: created pull request in repository '{repo}': '{title}'")
        self.register_tool("figma_export", lambda id: f"Figma: exported design layouts for frame ID '{id}'")
        self.register_tool("canva_export", lambda id: f"Canva: exported dynamic templates for layout ID '{id}'")
