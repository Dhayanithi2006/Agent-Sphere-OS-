import pytest
import asyncio
from app.core.shared import scheduler, model_router, supervisor, event_bus, checkpoint_manager, shared_memory
from app.core.shared import tool_manager
from app.core.config import settings

@pytest.fixture(autouse=True)
def configure_test_environment(request):
    """Automatically mock/stub LLM endpoints for unit tests, and bind async objects to the current loop."""
    # Re-bind event bus queue and locks to the current running event loop of this test
    event_bus._queue = asyncio.PriorityQueue()
    event_bus._lock = asyncio.Lock()
    event_bus._ws_locks = {}
    
    # Re-bind scheduler semaphore to the current running event loop of this test.
    # NOTE: asyncio.Semaphore() created outside a running loop is fine in Python 3.10+
    # because it lazily binds to the running loop on first `await`.  We still recreate
    # it here so each test gets a fresh, unacquired semaphore (no leftover acquisitions
    # from previous tests that would block the concurrent test).
    scheduler._semaphore = asyncio.Semaphore(scheduler.max_concurrency)
    
    # Check if the test is inside the end-to-end integration test file
    is_integration_test = "test_showrunner_pipeline" in request.module.__name__

    # Save original DB paths (before resetting to :memory:)
    orig_checkpoint_db = checkpoint_manager._db_path
    orig_memory_db = shared_memory._db_path

    # Switch to fresh in-memory databases for full test isolation.
    # IMPORTANT: use reset_for_test() instead of the raw "_connection = None" pattern.
    # The raw pattern races with any background asyncio task (e.g. kernel._resource_monitor_task)
    # that still holds a cursor on the old connection, causing:
    #   InterfaceError: bad parameter or other API misuse
    # reset_for_test() holds the thread lock throughout the swap so no coroutine can
    # observe a partially-reset state.
    checkpoint_manager.reset_for_test(":memory:")
    shared_memory.reset_for_test(":memory:")

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
    
    # Reset tool manager state to prevent cross-test contamination
    orig_tool_calls_count = tool_manager.tool_calls_count
    orig_tool_cache = dict(tool_manager._cache)
    tool_manager.tool_calls_count = 0
    tool_manager._cache.clear()

    yield
    
    # Restore tool manager state
    tool_manager.tool_calls_count = orig_tool_calls_count
    tool_manager._cache = orig_tool_cache
    
    # Restore original keys
    settings.qwen_api_key = orig_settings_key
    model_router.client.api_key = orig_router_key
    if "qwen" in model_router._providers and orig_provider_key is not None:
        model_router._providers["qwen"].client.api_key = orig_provider_key
        
    for agent_id, orig_key in orig_agent_keys.items():
        agent = supervisor._agents.get(agent_id)
        if agent and hasattr(agent, "client") and hasattr(agent.client, "api_key"):
            agent.client.api_key = orig_key

    # Restore original DB paths using the safe atomic reset.
    # The kernel.shutdown() in ensure_runtime (test_e2e_workflows.py) cancels the
    # resource monitor background task before we get here, so the lock is uncontested.
    # Using reset_for_test() instead of raw _connection = None eliminates the race
    # that caused InterfaceError in test_e2e_concurrent_workflows_and_scheduling.
    checkpoint_manager.reset_for_test(orig_checkpoint_db)
    shared_memory.reset_for_test(orig_memory_db)
