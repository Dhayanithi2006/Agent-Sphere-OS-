"""Planner agent for the AI Showrunner pipeline."""

from __future__ import annotations

import os
import json
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory, event_bus, recovery_engine, supervisor
from app.events.event_models import EventPriority


class ShowrunnerPlannerAgent(BaseAgent):
    """Planner Agent: Formulates the structured scene-by-scene script outline from movie goal."""

    def __init__(self, agent_id: str = "showrunner_planner", name: str = "showrunner_planner") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Planner")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Planner Agent")

        # Retrieve task pid for workspace
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        # 1. Retrieve attributes from payload or fallbacks
        movie_title = (
            (payload or {}).get("movie_title")
            or (payload or {}).get("task")
            or (payload or {}).get("movie_goal")
            or shared_memory.read("showrunner", "movie_goal")
            or "A default story about AI"
        )
        genre = (
            (payload or {}).get("genre")
            or shared_memory.read("showrunner", "genre")
            or "Sci-Fi"
        )
        duration = (
            (payload or {}).get("duration")
            or shared_memory.read("showrunner", "duration")
            or "30 sec"
        )
        target_audience = (
            (payload or {}).get("target_audience")
            or shared_memory.read("showrunner", "target_audience")
            or "General"
        )
        language = (
            (payload or {}).get("language")
            or shared_memory.read("showrunner", "language")
            or "English"
        )
        
        user = (payload or {}).get("user", "Alice")
        preferred_style = shared_memory.read("user_preferences", f"{user}:style") or "Pixar"
        style = (
            (payload or {}).get("style")
            or shared_memory.read("showrunner", "style")
            or preferred_style
        )

        # Persist properties in shared memory
        shared_memory.write("showrunner", "movie_goal", movie_title)
        shared_memory.write("showrunner", "genre", genre)
        shared_memory.write("showrunner", "duration", duration)
        shared_memory.write("showrunner", "target_audience", target_audience)
        shared_memory.write("showrunner", "language", language)
        shared_memory.write("showrunner", "style", style)

        # Emit PLANNER_STARTED event
        event_bus.publish(
            event_type="PLANNER_STARTED",
            payload={
                "pid": pid,
                "title": movie_title,
                "genre": genre,
                "style": style,
            },
            priority=EventPriority.MEDIUM,
        )

        # 2. Check Semantic Cache
        cached_scenes = shared_memory.read("cache", f"scenes:{movie_title}:{user}")
        if cached_scenes:
            try:
                # Ensure the cached version is valid structured JSON
                data = json.loads(cached_scenes)
                if isinstance(data, dict) and "scenes" in data:
                    self.logger.info("Semantic cache hit for Planner Agent!")
                    shared_memory.write("showrunner", "scenes", cached_scenes)
                    with open(os.path.join(workspace_dir, "planner.json"), "w", encoding="utf-8") as f:
                        f.write(cached_scenes)
                    
                    event_bus.publish(
                        event_type="PLANNER_COMPLETED",
                        payload={"pid": pid, "title": movie_title, "cached": True},
                        priority=EventPriority.MEDIUM,
                    )
                    
                    shared_memory.write("showrunner", "progress", "Planner: 100% (Cache Hit)")
                    return cached_scenes
            except Exception:
                pass

        # 3. Call Model Router using 'planner' task type (routes to qwen-max)
        prompt = (
            "You are the director of an autonomous AI movie studio. Based on the user's requirements:\n"
            f"- Title: '{movie_title}'\n"
            f"- Genre: '{genre}'\n"
            f"- Duration: '{duration}'\n"
            f"- Target Audience: '{target_audience}'\n"
            f"- Language: '{language}'\n"
            f"- Style: '{style}'\n\n"
            "Generate a scene-by-scene script outline. Break it down into exactly 3 consecutive scenes.\n"
            "For each scene, you MUST specify:\n"
            "- characters (array of characters present in scene)\n"
            "- location (specific location name)\n"
            "- camera_movement (specific camera action details, e.g. panning, zooming, close-up)\n"
            "- lighting (specific lighting style, e.g. dark, backlit, neon glow)\n"
            "- soundtrack_mood (e.g. suspenseful, orchestral, rock)\n"
            "- narration_style (voiceover tone, e.g. dramatic, energetic, soft)\n"
            "- transition_hint (e.g. cross-dissolve, fade, cut)\n"
            "Format your response as a single JSON object matching this schema exactly:\n"
            "{\n"
            "  \"title\": \"\",\n"
            "  \"genre\": \"\",\n"
            "  \"duration\": \"\",\n"
            "  \"characters\": [],\n"
            "  \"locations\": [],\n"
            "  \"summary\": \"\",\n"
            "  \"scenes\": [\n"
            "    {\n"
            "      \"scene_number\": 1,\n"
            "      \"title\": \"\",\n"
            "      \"description\": \"\",\n"
            "      \"characters\": [],\n"
            "      \"location\": \"\",\n"
            "      \"camera_movement\": \"\",\n"
            "      \"lighting\": \"\",\n"
            "      \"soundtrack_mood\": \"\",\n"
            "      \"narration_style\": \"\",\n"
            "      \"transition_hint\": \"\",\n"
            "      \"goal\": \"\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Return ONLY raw JSON. Do not include markdown code block styling or any other commentary."
        )

        shared_memory.write("showrunner", "progress", "Planner: 30% (Writing Story...)")
        # Log active model for frontend display
        active_model = model_router.get_active_model_for_task("planner")
        shared_memory.write("showrunner", "current_model", active_model)
        self.logger.info(f"Planner Agent using model: {active_model}")
        try:
            response = model_router.generate(prompt, "planner")

            # Clean response if markdown blocks are included
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()

            # Verify JSON correctness
            json.loads(response_clean)

            # Store in shared memory, workspace and semantic cache
            shared_memory.write("showrunner", "scenes", response_clean)
            shared_memory.write("cache", f"scenes:{movie_title}:{user}", response_clean)

            with open(os.path.join(workspace_dir, "planner.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)

            # Create Checkpoint via Recovery Engine
            recovery_engine.create_checkpoint(self.agent_id, {"scenes": response_clean, "pid": pid})

            # Emit PLANNER_COMPLETED event
            event_bus.publish(
                event_type="PLANNER_COMPLETED",
                payload={
                    "pid": pid,
                    "title": movie_title,
                    "output_file": os.path.join(workspace_dir, "planner.json"),
                },
                priority=EventPriority.MEDIUM,
            )

            shared_memory.write("showrunner", "progress", "Planner: 100% (Completed)")
            return response_clean
        except Exception as e:
            import traceback
            self.logger.exception("PLANNER FAILED")
            self.logger.error(f"Failed to query model router or parse JSON: {e}. Falling back to default outline.")
            
            # Invoke Recovery Engine to log/handle failure
            try:
                recovery_engine.recover(
                    failed_agent_id=self.agent_id,
                    payload={"error": str(e), "pid": pid}
                )
            except Exception as rec_err:
                self.logger.error(f"Recovery engine failure: {rec_err}")

            fallback_data = {
                "title": movie_title,
                "genre": genre,
                "duration": duration,
                "characters": ["Narrator", "Hero"],
                "locations": ["Spaceship", "Space"],
                "summary": "A space battle commercial outline.",
                "scenes": [
                    {
                        "scene_number": 1,
                        "title": "The Spark",
                        "description": f"A character discovers a glowing artifact representing the style: {style}.",
                        "characters": ["Narrator", "Hero"],
                        "location": "Dark Temple",
                        "camera_movement": "Slow zoom-in on the artifact",
                        "lighting": "Backlit blue glow",
                        "soundtrack_mood": "Eerie suspense",
                        "narration_style": "Dramatic mystery",
                        "transition_hint": "Fade-in from black",
                        "goal": "Introduce the artifact."
                    },
                    {
                        "scene_number": 2,
                        "title": "The Awakening",
                        "description": "The artifact activates, projecting a futuristic city layout in the air.",
                        "characters": ["Narrator", "Hero"],
                        "location": "Temple Chamber",
                        "camera_movement": "Wide pan around the holographic map",
                        "lighting": "Vibrant glowing pinks and neon lines",
                        "soundtrack_mood": "Epic orchestral swell",
                        "narration_style": "Awe-inspiring and grand",
                        "transition_hint": "Cross-dissolve to city layout",
                        "goal": "Activate the map."
                    },
                    {
                        "scene_number": 3,
                        "title": "The Journey",
                        "description": "The character steps forward, ready to venture into the new world.",
                        "characters": ["Narrator", "Hero"],
                        "location": "Temple Exit Gateway",
                        "camera_movement": "Over-the-shoulder tracking shot as they step forward",
                        "lighting": "Warm blinding golden portal light",
                        "soundtrack_mood": "Uplifting futuristic beats",
                        "narration_style": "Heroic action tone",
                        "transition_hint": "Fade to black",
                        "goal": "Begin the journey."
                    }
                ]
            }
            fallback = json.dumps(fallback_data)
            shared_memory.write("showrunner", "scenes", fallback)
            with open(os.path.join(workspace_dir, "planner.json"), "w", encoding="utf-8") as f:
                f.write(fallback)

            # Emit PLANNER_FAILED event
            event_bus.publish(
                event_type="PLANNER_FAILED",
                payload={"pid": pid, "title": movie_title, "error": str(e)},
                priority=EventPriority.HIGH,
            )

            shared_memory.write("showrunner", "progress", "Planner: 100% (Fallback)")
            return fallback
