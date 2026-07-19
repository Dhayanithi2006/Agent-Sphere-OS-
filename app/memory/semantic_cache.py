"""Semantic Cache service using embedded database vector similarity lookup."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from app.core.shared import shared_memory

# Responses containing these markers are invalid and must never be cached or served
_INVALID_MARKERS = (
    "[openai stub]",
    "[ERROR]",
    "stub execution",
    "not implemented",
    "fallback to a stub",
)


def _is_valid_response(value: str) -> bool:
    """Return True if the cached value is a real LLM response (not a stub/error)."""
    if not value or not value.strip():
        return False
    low = value.lower()
    return not any(marker.lower() in low for marker in _INVALID_MARKERS)


def run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously, handling thread-pool cases gracefully."""
    try:
        # Check if we are already in an active event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Create a new event loop in a sub-thread since the current thread has a loop running
        # (This is common when run from threadpools)
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    else:
        return asyncio.run(coro)


class SemanticCache:
    """Semantic Cache interface leveraging the local SQLite vector database."""

    def __init__(self, threshold: float = 0.90) -> None:
        self.threshold = threshold

    def get(self, category: str, prompt: str) -> Optional[str]:
        """Retrieve cached text value if a semantically similar query is found."""
        query_str = f"{category}:{prompt}"
        try:
            results = run_async(shared_memory.query_vector(query_str, top_k=1))
            if results:
                best_match = results[0]
                similarity = best_match.get("similarity", 0.0)
                if similarity >= self.threshold:
                    val = best_match.get("metadata", {}).get("value")
                    if val and _is_valid_response(val):
                        return val
        except Exception:
            pass
        return None

    def set(self, category: str, prompt: str, value: str) -> None:
        """Cache a text value under a hashed semantic vector — only if it's a real response."""
        if not _is_valid_response(value):
            return  # Never cache stub/error responses
        query_str = f"{category}:{prompt}"
        try:
            run_async(shared_memory.add_vector(
                text=query_str,
                metadata={
                    "category": category,
                    "prompt": prompt,
                    "value": value
                }
            ))
        except Exception:
            pass
