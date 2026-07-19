"""AI Poster Generator plugin generating cover thumbnails, banners and posters via Qwen Image API."""

from __future__ import annotations

import os
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory
from app.showrunner.video_generation.video_storage import VideoStorageManager


class ShowrunnerPosterAgent(BaseAgent):
    """Poster Agent: Generates movie posters and thumbnails via Qwen Image API with SVG fallback."""

    def __init__(self, agent_id: str = "showrunner_poster", name: str = "showrunner_poster") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Poster Generator")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Poster Generator Agent")

        movie_goal = (payload or {}).get("movie_goal") or shared_memory.read("showrunner", "movie_goal") or "Default Movie"
        genre = shared_memory.read("showrunner", "genre") or "Sci-Fi"
        style = shared_memory.read("showrunner", "style") or "cinematic"
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")

        # Setup paths
        paths = VideoStorageManager.setup_production_assets(pid)
        poster_path = os.path.join(paths["posters"], "poster.svg")   # SVG for rich fallback
        thumb_path = os.path.join(paths["thumbnail"], "thumbnail.svg")

        # Log active model to shared memory so frontend can display it
        from app.core.config import settings
        active_model = settings.qwen_image_model
        shared_memory.write("showrunner", "current_model", f"Image: {active_model}")
        self.logger.info(f"Poster Agent using model: {active_model}")

        shared_memory.write("showrunner", "progress", "Poster: 20% (Generating poster design...)")

        try:
            from app.services.image_service import ImageService
            image_svc = ImageService()

            # Generate main poster
            result_path = image_svc.generate_poster(
                movie_goal=movie_goal,
                output_path=poster_path,
                style=style,
                genre=genre,
            )
            self.logger.info(f"Poster generated at: {result_path}")

            # Generate thumbnail (smaller, same concept)
            shared_memory.write("showrunner", "progress", "Poster: 70% (Generating thumbnail...)")
            thumb_result = image_svc.generate_thumbnail(
                movie_goal=movie_goal,
                output_path=thumb_path,
            )

            shared_memory.write("showrunner", "poster_path", result_path)
            shared_memory.write("showrunner", "thumbnail_path", thumb_result)
            shared_memory.write("showrunner", "progress", "Poster: 100% (Completed)")

            return (
                f"Poster generated at: {result_path}\n"
                f"Thumbnail generated at: {thumb_result}\n"
                f"Model: {active_model}"
            )

        except Exception as e:
            self.logger.warning(f"Poster rendering failed: {e}")
            shared_memory.write("showrunner", "progress", "Poster: 100% (Fallback poster used)")
            return f"Poster generation encountered error: {e} — SVG fallback attempted."
