"""Prompt management utilities for agent instructions and templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PromptTemplate:
    """A reusable instruction template for an agent."""

    name: str
    content: str


class PromptManager:
    """Loads and renders prompt templates used by agents."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent.parent / "prompts")
        self._templates: dict[str, PromptTemplate] = {}

    def register_template(self, name: str, content: str) -> None:
        """Register a prompt template in memory."""
        self._templates[name] = PromptTemplate(name=name, content=content)

    def render(self, name: str, **context: Any) -> str:
        """Render a prompt template with the provided context."""
        template = self._templates.get(name)
        if template is None:
            raise KeyError(f"Prompt template '{name}' is not registered")
        rendered = template.content
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered
