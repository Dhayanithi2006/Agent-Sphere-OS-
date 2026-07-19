"""Unit and integration tests for Modules 19 to 35 (Memory, Context, Workflows, Dynamic Agents, Auth, Scheduler, Tools)."""

from __future__ import annotations

import pytest
import asyncio
from app.memory.memory_agent import MemoryAgent
from app.memory.semantic_context import enrich_prompt_with_memories
from app.runtime.workflow_engine import WorkflowEngine
from app.core.dynamic_agent_factory import spawn_dynamic_agent, destroy_dynamic_agent
from app.tools.registry import ToolRegistry
from app.llm.cost_optimizer import CostOptimizer
from app.runtime.scheduler import Scheduler
from app.api.auth import AuthController
from app.api.analytics import AnalyticsEngine
from app.api.marketplace import MarketplaceManager


def test_memory_agent_tier_ranking():
    """Verify that MemoryAgent correctly registers and persists memory items across tiers."""
    agent = MemoryAgent()
    agent.store_memory("Alice prefers anime styling", tier="long_term")
    memories = agent.recall_memories("anime", limit=1)
    
    assert len(memories) > 0
    assert "anime" in memories[0]["content"].lower()
    assert memories[0]["tier"] == "long_term"


def test_semantic_context_prompt_enrichment():
    """Verify that the Semantic Context Engine prefixes prompts with user preference presets."""
    agent = MemoryAgent()
    agent.store_memory("Bob prefers cold neon styling", tier="long_term")
    
    prompt = "Create a superhero logo using neon colors"
    enriched = enrich_prompt_with_memories(prompt)
    
    assert "Instructions: Respect the following recalled user memory profile:" in enriched
    assert "neon" in enriched


def test_workflow_engine_dags():
    """Verify that WorkflowEngine correctly resolves distinct task sequences for different formats."""
    movie_steps = WorkflowEngine.get_steps("movie")
    podcast_steps = WorkflowEngine.get_steps("podcast")
    ad_steps = WorkflowEngine.get_steps("advertisement")
    
    assert len(movie_steps) > 0
    # Movie pipeline has parallel and video/subtitle steps
    assert any(step[0] == "showrunner_parallel" for step in movie_steps)
    assert any(step[0] == "showrunner_video" for step in movie_steps)
    
    # Podcast does not have parallel storyboard/video
    assert not any(step[0] == "showrunner_storyboard" for step in podcast_steps)
    assert not any(step[0] == "showrunner_video" for step in podcast_steps)


def test_dynamic_agent_spawning_and_destroying():
    """Verify that transient agents can be registered at runtime and destroyed upon completion."""
    from app.core.shared import supervisor
    
    agent_id = "transient_translator"
    spawn_dynamic_agent(agent_id, "Translate following text into French:")
    
    assert agent_id in supervisor._agents
    
    # Execute the ephemeral agent
    agent = supervisor._agents[agent_id]
    result = agent.execute({"task": "Hello World"})
    assert len(result) > 0
    
    destroy_dynamic_agent(agent_id)
    assert agent_id not in supervisor._agents


def test_tool_registry():
    """Verify that the Tool Registry manages system calls and correctly routes executions."""
    reg = ToolRegistry()
    res = reg.execute_tool("slack_notify", "Deployment successful!")
    assert "Slack: broadcast notification" in res


def test_cost_optimizer():
    """Verify that CostOptimizer estimates budgets and returns comparative framework savings."""
    savings = CostOptimizer.calculate_remaining("movie", 0.0350)
    assert savings["estimated_total"] == 0.0760
    assert savings["remaining_budget"] > 0.0
    assert savings["savings_percent"] == 62.0


@pytest.mark.anyio
async def test_adaptive_scheduler():
    """Verify that AdaptiveScheduler handles queueing and dynamic concurrency worker count throttling."""
    sched = Scheduler(max_concurrency=2)
    
    async def sample_task():
        await asyncio.sleep(0.01)
        return "success"
        
    res = await sched.execute_task("test_item", sample_task)
    assert res == "success"


def test_authentication_permissions():
    """Verify AuthController parses headers and validates needed permission scopes."""
    # Correct admin token
    admin_info = AuthController.verify_token("Bearer admin_secret_token")
    assert admin_info["role"] == "admin"
    assert "marketplace" in admin_info["permissions"]
    
    # Correct creator token
    creator_info = AuthController.verify_token("Bearer creator_secret_token")
    assert creator_info["role"] == "creator"
    assert "write" in creator_info["permissions"]
    assert "marketplace" not in creator_info["permissions"]
    
    # Permission gating check
    AuthController.check_permission(admin_info, "delete") # Admin should pass
    
    with pytest.raises(Exception):
        AuthController.check_permission(creator_info, "marketplace") # Creator should fail


def test_analytics_benchmarks():
    """Verify AnalyticsEngine aggregates frame rates, render latency, and CrewAI cost benchmarks."""
    stats = AnalyticsEngine.get_system_analytics(current_cost=0.030, total_tokens=1000)
    assert stats["average_fps"] == 24.0
    assert stats["recovered_failures"] == 1
    assert stats["money_saved_usd"] > 0.0
    assert "crew_comparison" in stats


def test_marketplace_manager():
    """Verify MarketplaceManager lists store options and dynamically installs new plugins."""
    catalog = MarketplaceManager.list_catalog()
    assert len(catalog) > 0
    
    # Install Translation Agent
    success = MarketplaceManager.install_plugin("translation_agent")
    assert success
    
    from app.core.shared import supervisor
    assert "translation_agent" in supervisor._agents
