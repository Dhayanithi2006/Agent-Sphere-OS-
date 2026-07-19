"""Unit and integration tests for Module 12 (Plugin Manager)."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Generator
import pytest
from app.plugins.plugin_manager import PluginManager


# Valid mock agent template
VALID_AGENT_CODE = """from app.agents.base_agent import BaseAgent
from typing import Any

class CustomAgent(BaseAgent):
    def __init__(self, agent_id: str = "custom_agent_id", name: str = "custom_agent") -> None:
        super().__init__(agent_id=agent_id, name=name)

    def execute(self, prompt: str, **kwargs: Any) -> str:
        return f"Hello from CustomAgent: {prompt}"
"""

# Malicious mock agent templates violating AST checks
MALICIOUS_SUBPROCESS_CODE = """from app.agents.base_agent import BaseAgent
import subprocess

class MaliciousAgent(BaseAgent):
    def execute(self, prompt: str, **kwargs: Any) -> str:
        subprocess.run(["echo", "exploit"])
        return "malicious"
"""

MALICIOUS_EVAL_CODE = """from app.agents.base_agent import BaseAgent

class MaliciousAgent(BaseAgent):
    def execute(self, prompt: str, **kwargs: Any) -> str:
        eval("print('exploit')")
        return "malicious"
"""


@pytest.fixture
def temp_plugin_file() -> Generator[str, None, None]:
    """Fixture providing a temporary valid plugin python file."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write(VALID_AGENT_CODE)
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_malicious_subprocess_file() -> Generator[str, None, None]:
    """Fixture providing a temporary malicious python file using subprocess."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write(MALICIOUS_SUBPROCESS_CODE)
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_malicious_eval_file() -> Generator[str, None, None]:
    """Fixture providing a temporary malicious python file using eval."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write(MALICIOUS_EVAL_CODE)
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_valid_plugin_loading_and_execution(temp_plugin_file):
    """Verify that a valid plugin file is scanned, registered, and can execute."""
    pm = PluginManager()
    
    # Load plugin dynamically
    pm.load_plugin_from_file(
        file_path=temp_plugin_file,
        class_name="CustomAgent",
        agent_id="custom_agent_id"
    )

    assert pm.get_plugin_state("custom_agent_id") == "active"
    assert "custom_agent_id" in pm.list_agents()
    assert "custom_agent_id" in pm.list_active_plugins()

    # Instantiate and execute agent
    agent = pm.create_agent("custom_agent_id", name="MyCustomAgent")
    assert agent.name == "MyCustomAgent"
    assert agent.execute("test prompt") == "Hello from CustomAgent: test prompt"


def test_malicious_plugin_subprocess_blocked(temp_malicious_subprocess_file):
    """Verify that AST security scan blocks imports of forbidden modules like subprocess."""
    pm = PluginManager()

    with pytest.raises(PermissionError, match="Restricted module import 'subprocess' detected"):
        pm.load_plugin_from_file(
            file_path=temp_malicious_subprocess_file,
            class_name="MaliciousAgent",
            agent_id="malicious_sub"
        )

    # State must be marked as failed
    assert pm.get_plugin_state("malicious_sub") == "failed"


def test_malicious_plugin_eval_blocked(temp_malicious_eval_file):
    """Verify that AST security scan blocks forbidden function calls like eval."""
    pm = PluginManager()

    with pytest.raises(PermissionError, match="Restricted built-in call 'eval' detected"):
        pm.load_plugin_from_file(
            file_path=temp_malicious_eval_file,
            class_name="MaliciousAgent",
            agent_id="malicious_eval"
        )

    # State must be marked as failed
    assert pm.get_plugin_state("malicious_eval") == "failed"


def test_plugin_unload_and_reload_lifecycle(temp_plugin_file):
    """Verify lifecycle of unloading and reloading plugins."""
    pm = PluginManager()

    # Load
    pm.load_plugin_from_file(
        file_path=temp_plugin_file,
        class_name="CustomAgent",
        agent_id="custom_agent_id"
    )
    assert pm.get_plugin_state("custom_agent_id") == "active"

    # Unload
    pm.unload_plugin("custom_agent_id")
    assert pm.get_plugin_state("custom_agent_id") == "inactive"
    assert "custom_agent_id" not in pm.list_agents()

    # Attempt to instantiate unloaded agent raises KeyError
    with pytest.raises(KeyError, match="Plugin agent 'custom_agent_id' is not registered"):
        pm.create_agent("custom_agent_id")

    # Reload
    pm.reload_plugin("custom_agent_id")
    assert pm.get_plugin_state("custom_agent_id") == "active"
    assert "custom_agent_id" in pm.list_agents()

    # Can execute again
    agent = pm.create_agent("custom_agent_id")
    assert agent.execute("reloaded") == "Hello from CustomAgent: reloaded"
