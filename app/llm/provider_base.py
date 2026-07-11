"""Base classes for pluggable model providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseModelProvider(ABC):
    """Abstract base for an external model provider."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate response text from a prompt."""
        raise NotImplementedError
