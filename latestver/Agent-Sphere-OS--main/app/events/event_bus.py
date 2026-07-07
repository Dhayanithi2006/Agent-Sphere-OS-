"""Event bus for asynchronous runtime notifications."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    """Simple publish/subscribe event bus for runtime events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._broadcast: list[tuple[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Register a handler for an event."""
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any = None) -> None:
        """Dispatch an event to all subscribers."""
        self._broadcast.append((event_type, payload))
        for handler in self._subscribers.get(event_type, []):
            handler(payload)

    def broadcast_history(self) -> list[tuple[str, Any]]:
        """Return the recently published events for inspection."""
        return list(self._broadcast)
