"""Scene Queue Manager: Manages video queue pipeline statuses for the dashboard."""

from __future__ import annotations

from typing import Dict, Any, List
from app.core.logger import get_logger

logger = get_logger("agentsphere.video.queue")


class SceneQueueManager:
    """Orchestrates concurrent video rendering queues."""

    def __init__(self) -> None:
        self._queue: Dict[str, Dict[str, Any]] = {}

    def add_scene(self, scene_id: str, prompt: str) -> None:
        """Register a scene to the rendering pipeline."""
        self._queue[scene_id] = {
            "scene_id": scene_id,
            "prompt": prompt,
            "status": "submitted",
            "progress": 0,
            "error": None
        }
        logger.info(f"Scene Queue: Added '{scene_id}' to execution queue.")

    def update_status(self, scene_id: str, status: str, progress: int = 0, error: str | None = None) -> None:
        """Update a scene's render state."""
        if scene_id in self._queue:
            self._queue[scene_id]["status"] = status
            self._queue[scene_id]["progress"] = progress
            self._queue[scene_id]["error"] = error
            logger.info(f"Scene Queue: Scene '{scene_id}' updated to '{status}' ({progress}%)")

    def get_snapshot(self) -> List[Dict[str, Any]]:
        """Return the current queue state checklist."""
        return list(self._queue.values())

    def clear(self) -> None:
        """Reset the queue scheduler."""
        self._queue.clear()
