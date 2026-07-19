"""Tool Manager for routing, caching, logging, and retry-handling of all external tool execution."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from app.tools.tool_registry import ToolRegistry
from app.core.logging import get_logger

logger = get_logger("agentsphere.tool_manager")


class ToolManager:
    """Routes all external tool usage through the kernel, handling permissions, logging, retries, caching, and security."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or ToolRegistry()
        self._cache: Dict[str, Any] = {}
        # Maximum retries for tool execution
        self.max_retries = 3
        self.tool_calls_count = 0

    def execute(self, tool_id: str, arguments: Dict[str, Any], agent_id: Optional[str] = None) -> Any:
        """Route tool invocation through the kernel with security, caching, logging, and retries."""
        # Enforce max tool calls limit from kernel
        try:
            from app.core.shared import kernel
            if kernel.max_tool_calls is not None and self.tool_calls_count >= kernel.max_tool_calls:
                raise RuntimeError(
                    f"Tool execution blocked: Maximum tool calls limit ({kernel.max_tool_calls}) reached."
                )
        except ImportError:
            pass

        self.tool_calls_count += 1

        # Register a stub tool dynamically if not present in the registry
        if not self.registry.get_tool(tool_id):
            logger.warning("Tool Manager: Tool '%s' not registered. Automatically registering dynamic stub.", tool_id)
            self.registry.register_tool(
                tool_id=tool_id,
                name=f"Dynamic {tool_id}",
                description="Dynamically registered stub tool"
            )

        # 1. Security & Permission Check
        if not self.registry.has_permission(agent_id or "anonymous", tool_id):
            tool = self.registry.get_tool(tool_id)
            if tool and tool["required_permissions"]:
                raise PermissionError(
                    f"Access Denied: Agent '{agent_id}' lacks required permissions for tool '{tool_id}'."
                )

        # 2. Caching: Generate a cache key
        cache_key = f"{tool_id}:{str(sorted(arguments.items()))}"
        if cache_key in self._cache:
            logger.info("Tool Manager: Cache hit for tool '%s'", tool_id)
            return self._cache[cache_key]

        # 3. Logging & Execution with Retries
        logger.info(
            "Tool Manager: Executing tool '%s' for agent '%s' with args %s",
            tool_id, agent_id, arguments
        )
        
        # Real-time structured trace layout print
        print(f"\n[{agent_id.upper() if agent_id else 'SYSTEM'}]")
        print(f"Decision: Executing tool '{tool_id}'")
        print(f"Tool Selected: {tool_id}")
        print(f"Arguments: {arguments}")

        attempt = 0
        last_exception = None
        while attempt <= self.max_retries:
            try:
                # Route execution through the ToolRegistry
                result = self.registry.execute_tool(tool_id, arguments, agent_id)
                # Store in cache
                self._cache[cache_key] = result
                
                print(f"Result: {result}")
                print(f"Confidence: 100%")
                print(f"Status: SUCCESS\n")
                
                return result
            except Exception as e:
                attempt += 1
                last_exception = e
                logger.warning(
                    "Tool Manager: Attempt %d failed for tool '%s': %s",
                    attempt, tool_id, e
                )
                print(f"Status: FAILED (Attempt {attempt}/{self.max_retries + 1})\n")
                if attempt <= self.max_retries:
                    time.sleep(0.2)  # small delay before retry


        logger.error(
            "Tool Manager: Tool '%s' failed after %d retries.",
            tool_id, self.max_retries
        )
        raise last_exception or RuntimeError(f"Tool '{tool_id}' execution failed")
