"""Model provider implementation for Qwen Cloud-compatible endpoints."""

from __future__ import annotations

import os
from typing import Any

import requests

from app.llm.provider_base import BaseModelProvider
from app.core.logger import get_logger


class QwenProvider(BaseModelProvider):
    """A provider that routes prompts to Qwen Cloud endpoints."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str = "qwen-v1") -> None:
        super().__init__(name="qwen")
        self.base_url = base_url or os.getenv("AGENTSPHERE_QWEN_API_URL", "https://api.qwen.com/v1/chat/completions")
        self.api_key = api_key or os.getenv("AGENTSPHERE_QWEN_API_KEY")
        self.model = model
        self.logger = get_logger("agentsphere.llm.qwen_provider")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Send a prompt to the Qwen-compatible model endpoint."""
        if not self.api_key:
            self.logger.warning("Qwen API key is not configured, falling back to a stub response")
            return f"[qwen stub] {prompt}"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data:
            return ""

        if isinstance(data, dict):
            if "choices" in data and data["choices"]:
                delta = data["choices"][0].get("message")
                return delta.get("content", "") if isinstance(delta, dict) else str(delta)
            return str(data)

        return str(data)
