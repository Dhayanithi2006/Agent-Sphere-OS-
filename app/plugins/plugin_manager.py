"""Agent marketplace for loading plugins that extend the kernel with custom agents."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple
from app.agents.base_agent import BaseAgent
from app.core.logging import get_logger

logger = get_logger("agentsphere.plugins")


class PluginManager:
    """A registry for dynamically loading, unloading, and reloading agent plugins safely."""

    def __init__(self) -> None:
        self._agent_factories: Dict[str, Callable[..., BaseAgent]] = {}
        self._plugin_metadata: Dict[str, Dict[str, Any]] = {}
        self._plugin_states: Dict[str, str] = {}  # active, inactive, failed
        self._plugin_module_refs: Dict[str, Tuple[str, str]] = {}  # agent_id -> (path/module, class_name)

    def register_agent_factory(
        self, agent_id: str, factory: Callable[..., BaseAgent], metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an agent factory with metadata."""
        self._agent_factories[agent_id] = factory
        self._plugin_metadata[agent_id] = metadata or {"source": "builtin"}
        if agent_id not in self._plugin_states or self._plugin_states[agent_id] != "active":
            self._plugin_states[agent_id] = "active"

    def get_agent_factory(self, agent_id: str) -> Optional[Callable[..., BaseAgent]]:
        """Retrieve an agent factory by its ID."""
        return self._agent_factories.get(agent_id)

    def create_agent(self, agent_id: str, **kwargs: Any) -> BaseAgent:
        """Instantiate a registered agent class."""
        factory = self.get_agent_factory(agent_id)
        if factory is None:
            raise KeyError(f"Plugin agent '{agent_id}' is not registered")
        return factory(**kwargs)

    def list_agents(self) -> List[str]:
        """List all registered agent IDs."""
        return sorted(self._agent_factories.keys())

    def get_plugin_state(self, agent_id: str) -> str:
        """Query the current state of a plugin ("active", "inactive", "failed")."""
        return self._plugin_states.get(agent_id, "inactive")

    def list_active_plugins(self) -> List[str]:
        """List all active plugin IDs."""
        return sorted([k for k, v in self._plugin_states.items() if v == "active"])

    def unload_plugin(self, agent_id: str) -> None:
        """Unload and deactivate a registered agent plugin."""
        if agent_id not in self._agent_factories:
            raise KeyError(f"Plugin agent '{agent_id}' is not registered")
        self._agent_factories.pop(agent_id, None)
        self._plugin_states[agent_id] = "inactive"
        logger.info(f"Unloaded plugin agent: {agent_id}")

    def load_agent_plugin(
        self, module_path: str, class_name: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Load a plugin from a standard python import path."""
        try:
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            if not issubclass(agent_class, BaseAgent):
                raise TypeError("Loaded plugin class must inherit from BaseAgent")
            
            self.register_agent_factory(agent_id, agent_class, metadata=metadata)
            self._plugin_states[agent_id] = "active"
            self._plugin_module_refs[agent_id] = (module_path, class_name)
            logger.info(f"Loaded plugin agent '{agent_id}' from module '{module_path}'")
        except Exception as e:
            self._plugin_states[agent_id] = "failed"
            logger.error(f"Failed to load plugin '{agent_id}' from module '{module_path}': {e}")
            raise

    def load_plugin_from_file(
        self, file_path: str, class_name: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Scan, verify, and dynamically load an agent plugin from a .py file on disk."""
        # 1. Static AST Security Scan
        try:
            self._security_scan(file_path)
        except Exception as e:
            self._plugin_metadata[agent_id] = {
                "source": "file",
                "path": file_path,
                "error": str(e),
                **(metadata or {}),
            }
            self._plugin_states[agent_id] = "failed"
            logger.error(f"Security scan failed for plugin file '{file_path}': {e}")
            raise

        # 2. Dynamic Spec Import
        try:
            spec = importlib.util.spec_from_file_location(f"agentsphere.plugins.custom.{agent_id}", file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load import spec for file path: {file_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            agent_class = getattr(module, class_name)
            if not issubclass(agent_class, BaseAgent):
                raise TypeError("Loaded plugin class must inherit from BaseAgent")

            self.register_agent_factory(
                agent_id,
                agent_class,
                metadata={"source": "file", "path": file_path, **(metadata or {})},
            )
            self._plugin_states[agent_id] = "active"
            self._plugin_module_refs[agent_id] = (file_path, class_name)
            logger.info(f"Successfully loaded plugin agent '{agent_id}' from file '{file_path}'")
        except Exception as e:
            self._plugin_states[agent_id] = "failed"
            logger.error(f"Failed to dynamically import plugin file '{file_path}': {e}")
            raise

    def reload_plugin(self, agent_id: str) -> None:
        """Reload a previously loaded plugin, updating its module reference."""
        if agent_id not in self._plugin_module_refs:
            raise KeyError(f"Plugin '{agent_id}' has not been loaded with reload metadata.")

        path_or_module, class_name = self._plugin_module_refs[agent_id]
        if path_or_module.endswith(".py"):
            self.load_plugin_from_file(path_or_module, class_name, agent_id)
        else:
            if path_or_module in sys.modules:
                try:
                    importlib.reload(sys.modules[path_or_module])
                except Exception as e:
                    logger.warning(f"Could not reload module '{path_or_module}': {e}")
            self.load_agent_plugin(path_or_module, class_name, agent_id)
        logger.info(f"Reloaded plugin agent: {agent_id}")

    def _security_scan(self, file_path: str) -> None:
        """Scan the python file using AST for disallowed imports or calls (eval/exec)."""
        forbidden_modules = {"subprocess", "socket", "ctypes"}
        forbidden_calls = {"eval", "exec"}

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            raise PermissionError(f"Security scan failed: Syntax error in plugin: {e}")

        for node in ast.walk(tree):
            # Check import statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_modules:
                        raise PermissionError(
                            f"Security Violation: Restricted module import '{alias.name}' detected."
                        )
            # Check import from statements
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in forbidden_modules:
                    raise PermissionError(
                        f"Security Violation: Restricted module import '{node.module}' detected."
                    )
            # Check eval/exec call blocks
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in forbidden_calls:
                        raise PermissionError(
                            f"Security Violation: Restricted built-in call '{node.func.id}' detected."
                        )
