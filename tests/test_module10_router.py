"""Unit and integration tests for Module 10 (Model Router)."""

from __future__ import annotations

from typing import Any
import pytest
from app.llm.model_router import ModelRouter
from app.llm.provider_base import BaseModelProvider


class MockSuccessfulProvider(BaseModelProvider):
    """Mock model provider that returns a successful stub response."""

    def __init__(self, name: str, response: str = "mocked success response") -> None:
        super().__init__(name=name)
        self.response = response
        self.generate_calls = 0

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.generate_calls += 1
        return self.response


class MockFailingProvider(BaseModelProvider):
    """Mock model provider that raises an exception during generation."""

    def __init__(self, name: str) -> None:
        super().__init__(name=name)
        self.generate_calls = 0

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.generate_calls += 1
        raise ConnectionError(f"Provider {self.name} connection timed out")


def test_provider_registration_and_routing():
    """Verify that providers can be registered and tasks are routed to the primary provider."""
    router = ModelRouter()
    provider = MockSuccessfulProvider(name="test_provider", response="custom result")
    
    router.register_provider("custom", provider)
    router.set_route("coding", [("custom", "custom-model")])

    res = router.route("coding", "print hello world")
    assert res == "custom result"
    assert provider.generate_calls == 1


def test_routing_fallback_on_failure():
    """Verify fallback sequence failover to subsequent providers in the chain."""
    router = ModelRouter()
    failing_provider = MockFailingProvider(name="failing_prov")
    backup_provider = MockSuccessfulProvider(name="backup_prov", response="backup success")

    router.register_provider("failing", failing_provider)
    router.register_provider("backup", backup_provider)

    # Set route: failing is primary, backup is secondary fallback
    router.set_route("reasoning", [("failing", None), ("backup", None)])

    res = router.route("reasoning", "explain quantum computing")
    assert res == "backup success"
    assert failing_provider.generate_calls == 1
    assert backup_provider.generate_calls == 1


def test_token_and_cost_metrics_tracking():
    """Verify estimation of token usage counts and cost rates per model."""
    router = ModelRouter()
    # Prompt is "hello world" (2 words)
    # Output is "success hello world response" (4 words)
    provider = MockSuccessfulProvider(name="custom_prov", response="success hello world response")
    
    router.register_provider("custom", provider)
    # Map reasoning to gpt-4o rates (0.005 prompt / 0.015 completion per 1k tokens)
    router.set_route("reasoning", [("custom", "gpt-4o")])

    # Trigger call
    router.route("reasoning", "hello world")

    # Word estimations:
    # prompt: 2 words * 1.3 = 2 tokens
    # response: 4 words * 1.3 = 5 tokens
    # Cost: (2 / 1000) * 0.005 + (5 / 1000) * 0.015 = 0.00001 + 0.000075 = 0.000085
    metrics = router.get_usage_metrics()

    assert metrics["total_calls"] == 1
    assert metrics["total_prompt_tokens"] == 2
    assert metrics["total_completion_tokens"] == 5
    assert pytest.approx(metrics["total_cost"], rel=1e-5) == 0.000085

    # Check provider usage tracking breakdown
    assert "custom" in metrics["provider_usage"]
    assert metrics["provider_usage"]["custom"]["calls"] == 1
    assert metrics["provider_usage"]["custom"]["prompt_tokens"] == 2
    assert metrics["provider_usage"]["custom"]["completion_tokens"] == 5
    assert pytest.approx(metrics["provider_usage"]["custom"]["cost"], rel=1e-5) == 0.000085

    # Verify reset clears metrics
    router.reset_metrics()
    reset_metrics = router.get_usage_metrics()
    assert reset_metrics["total_calls"] == 0
    assert reset_metrics["total_cost"] == 0.0
    assert reset_metrics["provider_usage"] == {}
