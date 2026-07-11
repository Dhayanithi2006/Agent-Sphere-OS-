"""Model provider implementation for OpenAI endpoints."""

from __future__ import annotations

import os
from typing import Any

import openai

from app.llm.provider_base import BaseModelProvider
from app.core.logger import get_logger


class OpenAIProvider(BaseModelProvider):
    """A provider that routes prompts to OpenAI models."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(name="openai")
        self.api_key = api_key or os.getenv("AGENTSPHERE_OPENAI_API_KEY")
        self.model = model or os.getenv("AGENTSPHERE_OPENAI_MODEL", "gpt-4o-mini")
        self.logger = get_logger("agentsphere.llm.openai_provider")
        if self.api_key:
            openai.api_key = self.api_key

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text response using the configured OpenAI model."""
        if not self.api_key:
            self.logger.warning("OpenAI API key is not configured, falling back to a stub response")
            return f"[openai stub] {prompt}"

        messages = kwargs.pop("messages", None) or [{"role": "user", "content": prompt}]
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        choices = getattr(response, "choices", None) or response.get("choices", [])
        if choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else getattr(choices[0], "message", None)
            if isinstance(message, dict):
                return message.get("content", "")
            return str(message or "")

        return str(response)
