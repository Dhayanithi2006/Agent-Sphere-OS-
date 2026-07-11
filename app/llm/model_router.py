"""Routing utilities for selecting the appropriate language model."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider_base import BaseModelProvider
from app.llm.qwen_provider import QwenProvider


class ModelRouter:
    """Selects a model provider and routes prompts through the AI layer."""

    def __init__(self, providers: dict[str, BaseModelProvider] | None = None, default_provider: str = "qwen") -> None:
        self.logger = get_logger("agentsphere.llm.model_router")
        self.providers: dict[str, BaseModelProvider] = providers or {}
        self.default_provider = default_provider
        self._ensure_default_providers()

    def _ensure_default_providers(self) -> None:
        if "qwen" not in self.providers:
            self.providers["qwen"] = QwenProvider()
        if "openai" not in self.providers:
            self.providers["openai"] = OpenAIProvider()

    def register_provider(self, provider: BaseModelProvider) -> None:
        self.providers[provider.name] = provider

    def route(self, task_type: str, prompt: str, provider_name: str | None = None, **kwargs: Any) -> str:
        """Route a prompt to the selected provider and handle fallback."""
        provider_order = [provider_name] if provider_name else [self.default_provider, "qwen", "openai"]
        for key in provider_order:
            if not key:
                continue
            provider = self.providers.get(key)
            if provider is None:
                continue
            try:
                self.logger.debug("Routing task '%s' to provider '%s'", task_type, provider.name)
                return provider.generate(prompt, task_type=task_type, **kwargs)
            except Exception as error:  # pragma: no cover
                self.logger.exception("Provider %s failed, trying next provider", provider.name)
        self.logger.warning("All configured providers failed; returning fallback text")
        return f"[failed to route prompt] {prompt}"

    def chat(self, task_type: str, prompt: str, provider_name: str | None = None, **kwargs: Any) -> str:
        return self.route(task_type=task_type, prompt=prompt, provider_name=provider_name, **kwargs)
