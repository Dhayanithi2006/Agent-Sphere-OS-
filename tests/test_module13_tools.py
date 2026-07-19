"""Unit and integration tests for Module 13 (Tool Registry)."""

from __future__ import annotations

from typing import Any
import pytest
from app.tools.tool_registry import ToolRegistry


# Sample test function
def add_numbers(a: int, b: int) -> int:
    return a + b


@pytest.fixture
def clean_registry() -> ToolRegistry:
    """Fixture providing a fresh isolated ToolRegistry instance."""
    return ToolRegistry()


def test_tool_registration_with_schema(clean_registry):
    """Verify registering a tool with schema and description fields."""
    tr = clean_registry
    schema = {
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            "required": ["a", "b"]
        }
    }

    tr.register_tool(
        tool_id="add",
        name="Add Numbers",
        description="Adds two integers together",
        func=add_numbers,
        schema=schema
    )

    tool = tr.get_tool("add")
    assert tool is not None
    assert tool["name"] == "Add Numbers"
    assert tool["description"] == "Adds two integers together"
    assert tool["schema"] == schema


def test_tool_execution_parameter_validation(clean_registry):
    """Verify tool execution validation for missing required parameters."""
    tr = clean_registry
    schema = {
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            "required": ["a", "b"]
        }
    }

    tr.register_tool(
        tool_id="add",
        name="Add Numbers",
        description="Adds two integers together",
        func=add_numbers,
        schema=schema
    )

    # Valid execution
    res = tr.execute_tool("add", {"a": 10, "b": 15})
    assert res == 25

    # Invalid execution (missing required argument 'b')
    with pytest.raises(ValueError, match="Missing required parameter 'b'"):
        tr.execute_tool("add", {"a": 10})


def test_tool_execution_permission_gates(clean_registry):
    """Verify capability-based security permission gates for tool execution."""
    tr = clean_registry

    # Register tool requiring specific permission
    tr.register_tool(
        tool_id="shell",
        name="Run Shell",
        description="Execute system commands",
        required_permissions=["shell:execute"]
    )

    # 1. Anonymous execution block
    with pytest.raises(PermissionError, match="Anonymous execution blocked"):
        tr.execute_tool("shell", {})

    # 2. Unauthorized agent block
    with pytest.raises(PermissionError, match="Access Denied: Agent 'agent_coder' lacks required permissions"):
        tr.execute_tool("shell", {}, agent_id="agent_coder")

    # 3. Grant permission and execute successfully
    tr.grant_permission("agent_coder", "shell:execute")
    assert tr.has_permission("agent_coder", "shell") is True
    
    # Executing succeeds and invokes default stub function
    res = tr.execute_tool("shell", {"cmd": "ls"}, agent_id="agent_coder")
    assert "Stub execution of 'shell'" in res

    # 4. Revoke permission and verify blocking
    tr.revoke_permission("agent_coder", "shell:execute")
    assert tr.has_permission("agent_coder", "shell") is False

    with pytest.raises(PermissionError, match="Access Denied"):
        tr.execute_tool("shell", {}, agent_id="agent_coder")
