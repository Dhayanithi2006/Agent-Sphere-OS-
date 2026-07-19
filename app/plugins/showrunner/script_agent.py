"""Script agent for the AI Showrunner pipeline."""

from __future__ import annotations

import os
import json
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory, event_bus, recovery_engine, supervisor
from app.events.event_models import EventPriority


class ShowrunnerScriptAgent(BaseAgent):
    """Script Agent: Writes dialogue, action descriptions, and narration for the scenes."""

    def __init__(self, agent_id: str = "showrunner_script", name: str = "showrunner_script") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Script Writer")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Script Agent")

        # Retrieve task pid for workspace
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        user = (payload or {}).get("user", "Alice")
        movie_goal = shared_memory.read("showrunner", "movie_goal") or "A default story about AI"

        # Emit SCRIPT_STARTED event
        event_bus.publish(
            event_type="SCRIPT_STARTED",
            payload={"pid": pid, "movie_goal": movie_goal},
            priority=EventPriority.MEDIUM,
        )

        # 1. Fetch scenes from planner.json or shared memory fallback
        planner_path = os.path.join(workspace_dir, "planner.json")
        scenes_data = None
        movie_title = movie_goal

        if os.path.exists(planner_path):
            try:
                with open(planner_path, "r", encoding="utf-8") as f:
                    planner_data = json.load(f)
                scenes_data = planner_data.get("scenes", [])
                movie_title = planner_data.get("title", movie_goal)
            except Exception as e:
                self.logger.warning(f"Failed to read planner.json: {e}")

        if not scenes_data:
            scenes_json = shared_memory.read("showrunner", "scenes")
            if scenes_json:
                try:
                    parsed = json.loads(scenes_json)
                    scenes_data = parsed.get("scenes", parsed) if isinstance(parsed, dict) else parsed
                except Exception:
                    pass

        if not scenes_data:
            # Reconstruct fallback outline if nothing is available
            scenes_data = [
                {"scene_number": 1, "title": "The Spark", "description": "Explorer finds a glowing crystal in forest.", "goal": "Find spark"},
                {"scene_number": 2, "title": "The Awakening", "description": "Explorer touches crystal, map activates.", "goal": "Activate map"},
                {"scene_number": 3, "title": "The Journey", "description": "Explorer steps into futuristic city portal.", "goal": "Enter portal"}
            ]

        # 2. Check Semantic Cache
        cached_script = shared_memory.read("cache", f"script:{movie_goal}:{user}")
        if cached_script:
            try:
                # Validate cached script format
                script_parsed = json.loads(cached_script)
                self.logger.info("Semantic cache hit for Script Agent!")
                shared_memory.write("showrunner", "script", cached_script)
                
                # Save script.json and script.md
                with open(os.path.join(workspace_dir, "script.json"), "w", encoding="utf-8") as f:
                    f.write(cached_script)
                
                self._write_md_screenplay(workspace_dir, movie_title, script_parsed)

                # Emit SCRIPT_COMPLETED event
                event_bus.publish(
                    event_type="SCRIPT_COMPLETED",
                    payload={"pid": pid, "movie_title": movie_title, "cached": True},
                    priority=EventPriority.MEDIUM,
                )

                shared_memory.write("showrunner", "progress", "Script: 100% (Cache Hit)")
                return cached_script
            except Exception:
                pass

        shared_memory.write("showrunner", "progress", "Script: 20% (Writing Screenplay...)")

        # 3. Formulate prompt for writing script mapping to qwen-plus
        prompt = (
            "You are an expert screenwriter. Expand the following scene outline into a complete production screenplay.\n"
            f"Movie Title: {movie_title}\n"
            f"Scenes List:\n{json.dumps(scenes_data)}\n\n"
            "For each scene, design dialogues (with emotion tags) and write camera notes and narration text.\n"
            "Format your response as a single JSON object matching this schema exactly:\n"
            "{\n"
            "  \"title\": \"\",\n"
            "  \"scenes\": [\n"
            "    {\n"
            "      \"scene_number\": 1,\n"
            "      \"location\": \"\",\n"
            "      \"time\": \"\",\n"
            "      \"characters\": [],\n"
            "      \"dialogues\": [\n"
            "        {\n"
            "          \"character\": \"\",\n"
            "          \"emotion\": \"\",\n"
            "          \"text\": \"\"\n"
            "        }\n"
            "      ],\n"
            "      \"camera_notes\": \"\",\n"
            "      \"narration\": \"\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Return ONLY raw JSON. Do not include markdown code block styling or any commentary."
        )

        try:
            response = model_router.generate(prompt, "script")
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()

            # Validate JSON
            script_parsed = json.loads(response_clean)

            # Store in shared memory and cache
            shared_memory.write("showrunner", "script", response_clean)
            shared_memory.write("cache", f"script:{movie_goal}:{user}", response_clean)

            # Save script.json
            with open(os.path.join(workspace_dir, "script.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)

            # Generate script.md
            self._write_md_screenplay(workspace_dir, movie_title, script_parsed)

            # Save checkpoint
            recovery_engine.create_checkpoint(self.agent_id, {"script": response_clean, "pid": pid})

            # Emit SCRIPT_COMPLETED event
            event_bus.publish(
                event_type="SCRIPT_COMPLETED",
                payload={
                    "pid": pid,
                    "movie_title": movie_title,
                    "output_file": os.path.join(workspace_dir, "script.json"),
                },
                priority=EventPriority.MEDIUM,
            )

            shared_memory.write("showrunner", "progress", "Script: 100% (Completed)")
            return response_clean
        except Exception as e:
            self.logger.error(f"Script agent failed or generated invalid JSON: {e}")

            # Invoke Recovery Engine
            try:
                recovery_engine.recover(
                    failed_agent_id=self.agent_id,
                    payload={"error": str(e), "pid": pid}
                )
            except Exception as rec_err:
                self.logger.error(f"Recovery engine failure: {rec_err}")

            fallback_data = {
                "title": movie_title,
                "scenes": [
                    {
                        "scene_number": 1,
                        "location": "Dark Forest Path",
                        "time": "Night",
                        "characters": ["Explorer"],
                        "dialogues": [
                            {
                                "character": "Explorer",
                                "emotion": "curious",
                                "text": "What is this... it feels warm."
                            }
                        ],
                        "camera_notes": "A dark forest path. A lone explorer wearing a high-tech coat steps through the brush. In the center, a crystalline device glows with soft blue light.",
                        "narration": "In the depth of the forgotten forest, a light flickered, calling out to the brave."
                    },
                    {
                        "scene_number": 2,
                        "location": "Ancient Temple Ruins",
                        "time": "Night",
                        "characters": ["Explorer"],
                        "dialogues": [
                            {
                                "character": "Explorer",
                                "emotion": "amazed",
                                "text": "Incredible! The maps... they show Neo-Tokyo in the year 3000!"
                            }
                        ],
                        "camera_notes": "The explorer touches the crystal. Beams of light shoot upwards, creating a holographic map of a futuristic city with sky-trains and tall glass towers.",
                        "narration": "Touching the sphere awakened the history of a civilization long lost to time."
                    },
                    {
                        "scene_number": 3,
                        "location": "City Portal Gate",
                        "time": "Night",
                        "characters": ["Explorer"],
                        "dialogues": [
                            {
                                "character": "Explorer",
                                "emotion": "determined",
                                "text": "There's no turning back now. Let's see what the future holds."
                            }
                        ],
                        "camera_notes": "The hologram solidifies into a portal of light. The explorer steps in, disappearing into the neon city skyline.",
                        "narration": "With the path revealed, the explorer took a leap of faith into tomorrow."
                    }
                ]
            }
            fallback = json.dumps(fallback_data)
            shared_memory.write("showrunner", "script", fallback)
            with open(os.path.join(workspace_dir, "script.json"), "w", encoding="utf-8") as f:
                f.write(fallback)

            # Generate script.md from fallback
            self._write_md_screenplay(workspace_dir, movie_title, fallback_data)

            # Emit SCRIPT_FAILED event
            event_bus.publish(
                event_type="SCRIPT_FAILED",
                payload={"pid": pid, "movie_goal": movie_goal, "error": str(e)},
                priority=EventPriority.HIGH,
            )

            shared_memory.write("showrunner", "progress", "Script: 100% (Fallback)")
            return fallback

    def _write_md_screenplay(self, workspace_dir: str, title: str, script_data: dict[str, Any]) -> None:
        """Write the screenplay content formatted as standard Markdown script."""
        scenes = script_data.get("scenes", [])
        md_content = f"# Screenplay: {title}\n\n"
        for s in scenes:
            scene_num = s.get("scene_number", "?")
            loc = s.get("location", "Unknown")
            time_val = s.get("time", "Day")
            chars = ", ".join(s.get("characters", []))
            
            md_content += f"## Scene {scene_num}\n"
            md_content += f"**Location**: {loc} | **Time**: {time_val}\n\n"
            if chars:
                md_content += f"**Characters**: {chars}\n\n"
            md_content += f"**Camera Notes**: {s.get('camera_notes', '')}\n\n"
            md_content += f"**Narration**: *{s.get('narration', '')}*\n\n"
            
            dialogues = s.get("dialogues", [])
            if dialogues:
                md_content += "**Dialogue**:\n"
                for d in dialogues:
                    char_name = d.get("character", "Narrator")
                    emotion = d.get("emotion", "neutral")
                    text = d.get("text", "")
                    md_content += f"* **{char_name}** ({emotion}): \"{text}\"\n"
            md_content += "\n---\n\n"

        with open(os.path.join(workspace_dir, "script.md"), "w", encoding="utf-8") as f:
            f.write(md_content)
