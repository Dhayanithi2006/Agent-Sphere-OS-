"""Integration tests preventing regressions of infinite tool calling loops."""

from __future__ import annotations

import pytest
from app.runtime.execution_engine import ExecutionEngine
from app.agents.base_agent import BaseAgent
from typing import Any
import json
from app.core.shared import tool_manager
from app.llm.model_router import ModelRouter


class HistoryCheckingMockAgent(BaseAgent):
    """An agent that simulates an LLM receiving the payload context."""
    def __init__(self) -> None:
        super().__init__(agent_id="history_checker", name="History Checking Agent")
        
    def execute(self, payload: dict[str, Any] | None = None) -> str:
        # If payload["task"] contains 'Execution Memory / Tool History', we know it was injected
        task_content = (payload or {}).get("task", "")
        
        if "Execution Memory / Tool History" not in task_content:
            # Emulate the LLM requesting a tool because it doesn't see history
            return json.dumps({
                "thought": "I need data", 
                "tool_required": True, 
                "tool": "test_os_tool", 
                "arguments": {"x": "fastapi"}
            })
        else:
            # Emulate the LLM stopping because it sees the history
            return json.dumps({
                "thought": "I see the history now", 
                "tool_required": False, 
                "result": "Success"
            })


@pytest.mark.anyio
async def test_execution_engine_empty_payload_history_injection():
    """Verify that an empty initial payload successfully gets history injected into the 'task' key."""
    engine = ExecutionEngine()
    agent = HistoryCheckingMockAgent()
    
    from app.core.shared import tool_registry
    tool_registry.register_tool(
        tool_id="test_os_tool",
        name="Test Tool",
        description="test",
        func=lambda **kwargs: "Mock Result"
    )
    
    # Run with empty payload! This is what caused the bug (no predefined keys)
    empty_payload = {}
    
    result = engine.execute_agent(agent, payload=empty_payload)
    
    # If the bug exists, this would raise "Agent exceeded maximum iterative tool executions limit (10)"
    assert result.success is True
    assert result.output == "Success"
    
    # Verify the fallback task key was injected
    assert "Execution Memory / Tool History" in empty_payload.get("task", "")


def test_model_router_tool_instruction_contains_loop_breaker():
    """Verify that the model router explicitly instructs the LLM not to loop."""
    router = ModelRouter()
    
    # A prompt long enough to trigger the tool_instruction injection
    prompt = "This is a very long prompt " * 20
    
    # We can't easily intercept the final prompt without mocking the provider,
    # but we can look at the raw string in the source or route it to a mock provider.
    
    class MockProvider:
        def generate(self, p: str, **kwargs: Any) -> str:
            # Return the exact prompt it received so we can inspect it
            return p
            
    router.register_provider("mock", MockProvider())
    router.set_route("test_task", [("mock", None)])
    
    final_prompt = router.generate(prompt, task_type="test_task")
    
    # Verify the critical safeguard is present
    assert "CRITICAL: If the tool results already exist in the Execution Memory / Tool History, DO NOT call the tool again" in final_prompt

