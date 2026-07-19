import pytest
import asyncio
from app.core.shared import scheduler, model_router, supervisor, event_bus
from app.core.config import settings

@pytest.fixture(autouse=True)
def configure_test_environment(request):
    """Automatically mock/stub LLM endpoints for unit tests, and bind async objects to the current loop."""
    # Re-bind event bus queue and locks to the current running event loop of this test
    event_bus._queue = asyncio.PriorityQueue()
    event_bus._lock = asyncio.Lock()
    event_bus._ws_locks = {}
    
    # Re-bind scheduler semaphore to the current running event loop of this test
    scheduler._semaphore = asyncio.Semaphore(scheduler.max_concurrency)
    
    # Check if the test is inside the end-to-end integration test file
    is_integration_test = "test_showrunner_pipeline" in request.module.__name__
    
    if not is_integration_test:
        # Save original settings
        orig_settings_key = settings.qwen_api_key
        orig_router_key = model_router.client.api_key
        orig_provider_key = None
        if "qwen" in model_router._providers:
            orig_provider_key = model_router._providers["qwen"].client.api_key
            
        # Save original agent client keys
        orig_agent_keys = {}
        for agent_id, agent in supervisor._agents.items():
            if hasattr(agent, "client") and hasattr(agent.client, "api_key"):
                orig_agent_keys[agent_id] = agent.client.api_key
        
        # Override to mock mode
        settings.qwen_api_key = "mock-key"
        model_router.client.api_key = "mock-key"
        if "qwen" in model_router._providers:
            model_router._providers["qwen"].client.api_key = "mock-key"
            
        for agent_id, agent in supervisor._agents.items():
            if hasattr(agent, "client") and hasattr(agent.client, "api_key"):
                agent.client.api_key = "mock-key"
            
        # Clean scheduler state
        scheduler.resume_scheduler()
        scheduler._queue.clear()
        scheduler._paused.clear()
        scheduler._active.clear()
        
        yield
        
        # Restore original keys
        settings.qwen_api_key = orig_settings_key
        model_router.client.api_key = orig_router_key
        if "qwen" in model_router._providers and orig_provider_key is not None:
            model_router._providers["qwen"].client.api_key = orig_provider_key
            
        for agent_id, orig_key in orig_agent_keys.items():
            agent = supervisor._agents.get(agent_id)
            if agent and hasattr(agent, "client") and hasattr(agent.client, "api_key"):
                agent.client.api_key = orig_key
    else:
        # For integration tests, just reset scheduler
        scheduler.resume_scheduler()
        scheduler._queue.clear()
        scheduler._paused.clear()
        scheduler._active.clear()
        yield
