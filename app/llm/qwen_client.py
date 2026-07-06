"""Thin client wrapper for Qwen-compatible LLM APIs."""

from __future__ import annotations

from typing import Any


class QwenClient:
    """A minimal client abstraction for a Qwen-compatible backend."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = base_url or "https://api.example.com"
        self.api_key = api_key

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response using the configured LLM endpoint."""
        return f"[qwen] {prompt[:80]}"
