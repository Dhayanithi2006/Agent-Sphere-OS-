"""Tool registry for AgentSphere OS shared operating system services."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set
from app.core.logging import get_logger

logger = get_logger("agentsphere.tools")


class ToolRegistry:
    """Registry of tools available to agents and the runtime, featuring schema checks and capability gates."""

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}
        # Map agent_id -> set of granted permission strings (capabilities)
        self._agent_permissions: Dict[str, Set[str]] = {}
        self._init_system_tools()

    def _init_system_tools(self) -> None:
        from app.tools.system_tools import (
            search_web, read_url, git_clone, pytest_tool, python_runner, docker_tool, filesystem_tool, database_tool
        )
        self.register_tool("search_web", "Search Web", "Search the web using DuckDuckGo", search_web)
        self.register_tool("read_url", "Read URL", "Fetch URL content", read_url)
        self.register_tool("git_clone", "Git Clone", "Clone repository", git_clone)
        self.register_tool("pytest", "Pytest", "Run tests", pytest_tool)
        self.register_tool("python_runner", "Python Runner", "Run Python code", python_runner)
        self.register_tool("docker", "Docker", "Run docker command", docker_tool)
        self.register_tool("filesystem", "Filesystem", "Read, write or list files", filesystem_tool)
        self.register_tool("database", "Database", "Query database", database_tool)

        # Reflection tool plugin loader (Phase 6)
        import os
        import importlib.util
        import sys
        import inspect
        
        plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "tools"))
        if os.path.exists(plugins_dir):
            for file in os.listdir(plugins_dir):
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = f"app.plugins.tools.{file[:-3]}"
                    file_path = os.path.join(plugins_dir, file)
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, file_path)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[module_name] = module
                            spec.loader.exec_module(module)
                            
                            for name, val in inspect.getmembers(module):
                                if inspect.isfunction(val) and name.startswith("tool_"):
                                    tool_id = name[5:]
                                    self.register_tool(
                                        tool_id=tool_id,
                                        name=tool_id.replace("_", " ").title(),
                                        description=val.__doc__ or f"Reflection plugin tool: {tool_id}",
                                        func=val
                                    )
                                    logger.info(f"Dynamically registered tool plugin '{tool_id}'")
                    except Exception as e:
                        logger.error(f"Failed to load tool plugin '{file}': {e}")

    def register_tool(
        self,
        tool_id: str,
        name: str,
        description: str,
        func: Optional[Callable[..., Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
        required_permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a tool with its execution callable, parameter schema, and permission rules."""
        # Use a default stub execution callable if not provided for backward compatibility
        def default_stub(**kwargs: Any) -> str:
            return f"Stub execution of '{tool_id}' with args: {kwargs}"

        self._tools[tool_id] = {
            "id": tool_id,
            "name": name,
            "description": description,
            "func": func or default_stub,
            "schema": schema or {},
            "required_permissions": required_permissions or [],
            "metadata": metadata or {},
        }
        logger.info(f"Registered tool: {tool_id} (Required permissions={required_permissions})")

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a tool's details by its ID."""
        return self._tools.get(tool_id)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return list(self._tools.values())

    def grant_permission(self, agent_id: str, permission: str) -> None:
        """Grant a specific permission capability to an agent/process."""
        if agent_id not in self._agent_permissions:
            self._agent_permissions[agent_id] = set()
        self._agent_permissions[agent_id].add(permission)
        logger.info(f"Granted permission '{permission}' to agent '{agent_id}'")

    def revoke_permission(self, agent_id: str, permission: str) -> None:
        """Revoke a permission capability from an agent/process."""
        if agent_id in self._agent_permissions:
            self._agent_permissions[agent_id].discard(permission)
            logger.info(f"Revoked permission '{permission}' from agent '{agent_id}'")

    def has_permission(self, agent_id: str, tool_id: str) -> bool:
        """Check if an agent has all required permissions to execute a tool."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False

        required = tool["required_permissions"]
        if not required:
            return True

        granted = self._agent_permissions.get(agent_id, set())
        # Agent must possess every required permission
        return all(perm in granted for perm in required)

    def execute_tool(self, tool_id: str, arguments: Dict[str, Any], agent_id: Optional[str] = None) -> Any:
        """Validate permissions and arguments, then execute the registered tool callable."""
        tool = self.get_tool(tool_id)
        if not tool:
            raise KeyError(f"Tool '{tool_id}' is not registered.")

        # 1. Permission Capability Gate Audit
        if tool["required_permissions"]:
            if agent_id is None:
                raise PermissionError(
                    f"Anonymous execution blocked. Tool '{tool_id}' requires permissions: "
                    f"{tool['required_permissions']}"
                )
            if not self.has_permission(agent_id, tool_id):
                granted = list(self._agent_permissions.get(agent_id, set()))
                raise PermissionError(
                    f"Access Denied: Agent '{agent_id}' lacks required permissions for tool '{tool_id}'. "
                    f"Required: {tool['required_permissions']}, Granted: {granted}"
                )

        # 2. JSON-Schema Parameter Validation
        schema = tool["schema"]
        if schema and "parameters" in schema:
            params = schema["parameters"]
            if "required" in params:
                for req_param in params["required"]:
                    if req_param not in arguments:
                        raise ValueError(
                            f"Argument Validation Error for tool '{tool_id}': "
                            f"Missing required parameter '{req_param}'"
                        )

        # 3. Execution
        import time
        print("=" * 60)
        print(f"TOOL INVOKED : {tool_id}")
        print(f"ARGUMENTS    : {arguments}")
        start = time.time()
        func = tool["func"]
        try:
            res = func(**arguments)
            print("STATUS       : SUCCESS")
            print(f"DURATION     : {time.time() - start:.2f}s")
            print("=" * 60)
            return res
        except Exception as e:
            print("STATUS       : FAILED")
            print(f"DURATION     : {time.time() - start:.2f}s")
            print("=" * 60)
            logger.error(f"Execution failed for tool '{tool_id}' with args {arguments}: {e}")
            raise
