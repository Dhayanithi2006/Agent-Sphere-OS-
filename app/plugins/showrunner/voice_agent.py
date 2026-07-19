"""Voice selection agent for the AI Showrunner pipeline."""

from __future__ import annotations

import json
import os
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.shared import shared_memory


class ShowrunnerVoiceAgent(BaseAgent):
    """Voice Agent: Selects and configures audio voice models based on user preferences.

    Uses a deterministic built-in voice catalog instead of asking the LLM to
    call external tools (which caused infinite search_tts_models loops).
    """

    # Built-in voice catalog — deterministic lookup, no LLM tool loop.
    VOICE_CATALOG = [
        {"voice_id": "female-young-01",    "pitch": "medium-high", "accent": "US English", "gender": "female"},
        {"voice_id": "female-mature-01",   "pitch": "medium",      "accent": "US English", "gender": "female"},
        {"voice_id": "female-soft-01",     "pitch": "high",        "accent": "UK English", "gender": "female"},
        {"voice_id": "male-deep-01",       "pitch": "low",         "accent": "US English", "gender": "male"},
        {"voice_id": "male-warm-01",       "pitch": "medium-low",  "accent": "US English", "gender": "male"},
        {"voice_id": "male-energetic-01",  "pitch": "medium",      "accent": "US English", "gender": "male"},
    ]

    def __init__(self, agent_id: str = "showrunner_voice", name: str = "showrunner_voice") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Voice Selection Agent")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Voice Agent")

        movie_goal = (payload or {}).get("task") or (payload or {}).get("movie_goal") or ""
        if not movie_goal:
            movie_goal = shared_memory.read("showrunner", "movie_goal") or "A default story about AI"

        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        user = (payload or {}).get("user", "Alice")
        preferred_voice = shared_memory.read("user_preferences", f"{user}:voice") or "Female"
        preferred_lang = shared_memory.read("user_preferences", f"{user}:language") or "English"

        # Check cache
        cached = shared_memory.read("cache", f"voice:{movie_goal}:{user}")
        if cached:
            self.logger.info("Semantic cache hit for Voice Agent!")
            shared_memory.write("showrunner", "voice_selection", cached)
            try:
                with open(os.path.join(workspace_dir, "voice_selection.json"), "w", encoding="utf-8") as f:
                    f.write(cached)
            except Exception:
                pass
            shared_memory.write("showrunner", "progress", "Voice: 100% (Cache Hit)")
            return cached

        shared_memory.write("showrunner", "progress", "Voice: 40% (Selecting acoustic voice talent...)")

        # Deterministic selection from built-in catalog — prevents search_tts_models tool loops.
        pv = preferred_voice.lower()
        best = None
        for v in self.VOICE_CATALOG:
            if v["gender"] == pv:
                best = v
                break
        if best is None:
            best = self.VOICE_CATALOG[0]  # Default: female-young-01

        response_clean = json.dumps({
            "voice_id": best["voice_id"],
            "pitch": best["pitch"],
            "accent": best["accent"],
            "language": preferred_lang,
        })

        try:
            shared_memory.write("showrunner", "voice_selection", response_clean)
            shared_memory.write("cache", f"voice:{movie_goal}:{user}", response_clean)

            with open(os.path.join(workspace_dir, "voice_selection.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)

            shared_memory.write("showrunner", "progress", "Voice: 100% (Completed)")
            self.logger.info("Voice selection completed: %s", response_clean)
            return response_clean
        except Exception as e:
            self.logger.error(f"Voice agent save failed: {e}")
            # Return the selection even if save fails
            return response_clean
