"""Asynchronous Event Bus supporting priority dispatch, persistence, DLQ and replay."""

from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from fastapi import WebSocket

from app.core.config import settings as default_settings, AppSettings
from app.core.logging import get_logger
from app.events.event_models import Event, EventPriority

logger = get_logger("agentsphere.event_bus")


class EventBus:
    """Publish-Subscribe Event Bus with scheduling and JSONL persistence."""

    def __init__(self, settings: AppSettings = default_settings) -> None:
        self.settings = settings
        self._subscribers: Dict[str, List[Callable[[Any], Any]]] = defaultdict(list)
        
        # Async Queue and counter for sorting items in PriorityQueue
        self._queue: asyncio.PriorityQueue[tuple[int, int, Event]] = asyncio.PriorityQueue()
        self._counter = 0
        
        self._history: List[Event] = []
        self._broadcast: List[tuple[str, Any, str]] = []  # Backward compatibility trace
        self._websockets: List[WebSocket] = []
        self._ws_locks: Dict[WebSocket, asyncio.Lock] = {}
        self._dispatch_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: Callable[[Any], Any]) -> None:
        """Register a handler callback for an event type."""
        self._subscribers[event_type].append(handler)
        logger.info(f"Handler registered for event type '{event_type}'")

    def publish(self, event_type: str, payload: Any = None, priority: EventPriority = EventPriority.MEDIUM) -> None:
        """Publish an event to subscribers. Automatically chooses sync/async execution path."""
        event = Event(event_type=event_type, payload=payload, priority=priority)
        self._history.append(event)
        self._broadcast.append((event_type, payload, event.timestamp.isoformat()))

        # Always persist synchronously — the append is O(bytes) and must be visible immediately
        # so that replay() called right after publish() sees the events (required by unit tests).
        self._persist_sync(event, self.settings.event_log_path)

        # Check if an event loop is running
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                self._counter += 1
                # Negative priority value ensures higher priority (e.g. HIGH=2) is processed first
                loop.create_task(self._queue.put((-priority.value, self._counter, event)))
                return
        except RuntimeError:
            pass

        # Fallback to direct synchronous execution (e.g. during legacy unit tests / startup)
        self._dispatch_sync(event)


    async def start(self) -> None:
        """Start the background dispatch processor loop."""
        async with self._lock:
            if self._dispatch_task and not self._dispatch_task.done():
                return
            self._dispatch_task = asyncio.create_task(self._dispatch_loop())
            logger.info("Asynchronous event dispatch loop started")

    async def stop(self) -> None:
        """Cancel and clean up the background dispatch loop."""
        async with self._lock:
            if self._dispatch_task:
                self._dispatch_task.cancel()
                try:
                    await self._dispatch_task
                except asyncio.CancelledError:
                    pass
                self._dispatch_task = None
                logger.info("Asynchronous event dispatch loop stopped")

    def register_websocket(self, websocket: WebSocket) -> None:
        """Register a WebSocket client for real-time broadcasts."""
        self._websockets.append(websocket)
        self._ws_locks[websocket] = asyncio.Lock()
        logger.info("WebSocket registered to EventBus")

    def unregister_websocket(self, websocket: WebSocket) -> None:
        """Deregister a WebSocket client."""
        if websocket in self._websockets:
            self._websockets.remove(websocket)
        self._ws_locks.pop(websocket, None)
        logger.info("WebSocket unregistered from EventBus")

    async def replay(self, event_type: Optional[str] = None, since: Optional[datetime] = None, dispatch: bool = False) -> List[Event]:
        """Read past events from the JSONL log, filtering and optionally re-running them."""
        events: List[Event] = []
        if not os.path.exists(self.settings.event_log_path):
            return []

        try:
            with open(self.settings.event_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    event = Event.model_validate_json(line)
                    
                    if event_type and event.event_type != event_type:
                        continue
                    if since and event.timestamp < since:
                        continue
                        
                    events.append(event)
            
            if dispatch:
                for ev in events:
                    await self._dispatch_async(ev)
        except Exception as exc:
            logger.error(f"Event replay failed: {exc}")

        return events

    def broadcast_history(self) -> List[tuple[str, Any]]:
        """Retrieve historical broadcast log (legacy compatibility)."""
        return [(t, p) for t, p, _ in self._broadcast]

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent events in dict form (legacy compatibility)."""
        return [
            {"type": event_type, "payload": payload, "timestamp": ts}
            for event_type, payload, ts in self._broadcast[-limit:]
        ]

    async def _dispatch_loop(self) -> None:
        """Main queue execution consumer loop."""
        while True:
            try:
                # Pop event from the priority queue
                _, _, event = await self._queue.get()

                # Broadcast to connected WebSockets
                await self._broadcast_to_websockets(event)

                # Process event handlers asynchronously
                await self._dispatch_async(event)

                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event dispatch loop encounter: {e}")
                await asyncio.sleep(0.1)

    async def _dispatch_async(self, event: Event) -> None:
        """Asynchronously dispatch an event to registered callbacks."""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event.payload)
                else:
                    handler(event.payload)
            except Exception as exc:
                logger.exception(f"Async subscriber execution failed for event '{event.event_type}'")
                await self._route_to_dlq(event, str(exc))

    def _dispatch_sync(self, event: Event) -> None:
        """Synchronously dispatch an event to registered callbacks (fallback)."""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event.payload)
            except Exception as exc:
                logger.exception(f"Sync subscriber execution failed for event '{event.event_type}'")
                self._persist_sync(event, self.settings.dlq_log_path)

    async def _route_to_dlq(self, event: Event, error_message: str) -> None:
        """Record and route a failing event to the Dead Letter Queue (DLQ)."""
        event.error = error_message
        self._persist_sync(event, self.settings.dlq_log_path)
        logger.warning(f"Event '{event.event_id}' routed to Dead Letter Queue (DLQ) due to: {error_message}")

    async def _broadcast_to_websockets(self, event: Event) -> None:
        """Broadcast events to all registered browser/client WebSockets."""
        closed_sockets = []
        for ws in list(self._websockets):
            lock = self._ws_locks.get(ws)
            try:
                if lock:
                    async with lock:
                        await ws.send_json({
                            "type": "event",
                            "event_type": event.event_type,
                            "priority": event.priority.name,
                            "timestamp": event.timestamp.isoformat(),
                            "payload": event.payload,
                        })
                else:
                    await ws.send_json({
                        "type": "event",
                        "event_type": event.event_type,
                        "priority": event.priority.name,
                        "timestamp": event.timestamp.isoformat(),
                        "payload": event.payload,
                    })
            except Exception:
                closed_sockets.append(ws)

        for ws in closed_sockets:
            if ws in self._websockets:
                self._websockets.remove(ws)
            self._ws_locks.pop(ws, None)

    def _persist_sync(self, event: Event, file_path: str) -> None:
        """Write an event record to a JSONL log file synchronously."""
        try:
            # Ensure folder exists
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")
        except Exception as exc:
            logger.error(f"Persisting to {file_path} failed: {exc}")
