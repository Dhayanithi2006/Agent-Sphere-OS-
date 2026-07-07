"""Routing utilities for selecting the appropriate language model."""

from __future__ import annotations

from typing import Any

from app.llm.qwen_client import QwenClient


class ModelRouter:
    """Selects a model client based on task requirements."""

    def __init__(self, client: QwenClient | None = None) -> None:
        self.client = client or QwenClient()

    def route(self, task_type: str, prompt: str, **kwargs: Any) -> str:
        """Route a prompt to the selected backend client."""
        return self.client.generate(prompt, task_type=task_type, **kwargs)
