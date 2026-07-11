"""Deprecated Qwen client shim retained for compatibility."""

from __future__ import annotations

from typing import Any


class QwenClient:
    """A deprecated compatibility wrapper around the Qwen provider."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a stubbed response for legacy consumers."""
        return f"[qwen stub] {prompt[:80]}"
