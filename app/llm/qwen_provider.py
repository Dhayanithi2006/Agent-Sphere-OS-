"""Model provider implementation for Qwen Cloud-compatible endpoints."""

from __future__ import annotations

import os
from typing import Any

import requests

from app.llm.provider_base import BaseModelProvider
from app.core.logger import get_logger


class QwenProvider(BaseModelProvider):
    """A provider that routes prompts to Qwen Cloud endpoints using QwenClient."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str = "qwen-max") -> None:
        super().__init__(name="qwen")
        from app.llm.qwen_client import QwenClient
        self.client = QwenClient(base_url=base_url, api_key=api_key, model=model)
        self.model = model
        self.logger = get_logger("agentsphere.llm.qwen_provider")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Send a prompt to the Qwen-compatible model endpoint using unified QwenClient."""
        model_override = kwargs.pop("model", self.model)
        res = self.client.generate(prompt, model=model_override, **kwargs)
        if isinstance(res, str):
            return res
        # If generator/stream is returned, compile it to string
        return "".join(list(res))

