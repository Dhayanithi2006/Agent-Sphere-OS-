"""Scene planner agent for the AI Showrunner pipeline."""

from __future__ import annotations

import os
import json
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory


class ShowrunnerSceneAgent(BaseAgent):
    """Scene Agent: Decodes visual boards into generator instruction parameters."""

    def __init__(self, agent_id: str = "showrunner_scene", name: str = "showrunner_scene") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Scene Planner")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Scene Planner Agent")
        
        # 1. Fetch storyboard
        storyboard_json = shared_memory.read("showrunner", "storyboard")
        if not storyboard_json:
            raise ValueError("No storyboard found in shared memory. Ensure Storyboard Agent runs first.")

        # Retrieve task pid for workspace
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        shared_memory.write("showrunner", "progress", "Scene Planner: 50% (Extracting Parameters...)")

        # 2. Call Model Router using 'scene' task type (routes to qwen-plus)
        prompt = (
            "You are a technical director. Translate the following storyboard panels into concrete instructions "
            "for an AI Video Generation model (Wan Video / HappyHorse). "
            f"Storyboard:\n{storyboard_json}\n\n"
            "For each scene, extract:\n"
            "1. Scene description (the subject and action)\n"
            "2. Camera movement (e.g. Pan left, Zoom in, Low-angle tracking)\n"
            "3. Lighting setup (e.g. Volumetric neon lighting, cinematic backlighting, dim ambient)\n"
            "4. Duration (an integer from 3 to 10 seconds)\n"
            "Format your response as a JSON array of scene parameters. Example format:\n"
            '[{"scene_number": 1, "prompt": "...", "camera": "...", "lighting": "...", "duration": 5}]\n'
            "Return ONLY raw JSON."
        )

        try:
            response = model_router.generate(prompt, "scene")
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()

            json.loads(response_clean)

            shared_memory.write("showrunner", "scene_params", response_clean)
            
            # Save to workspace
            with open(os.path.join(workspace_dir, "scene_params.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)

            shared_memory.write("showrunner", "progress", "Scene Planner: 100% (Completed)")
            return response_clean
        except Exception as e:
            self.logger.warning(f"Scene planner agent failed: {e}")
            fallback = json.dumps([
                {
                    "scene_number": 1,
                    "prompt": "An explorer standing on a dark forest path looking down at a bright glowing blue crystal on the floor.",
                    "camera": "Slow zoom in, low-angle shot, cinematic slide",
                    "lighting": "Volumetric cyan glow, dim ambient forest light, high contrast",
                    "duration": 5
                },
                {
                    "scene_number": 2,
                    "prompt": "A glowing holographic city grid map rising out of the blue crystal inside the forest, explorer with amazed expression.",
                    "camera": "Static low-angle shot, looking up from the crystal",
                    "lighting": "Vibrant glowing pink and purple neon hologram lines, high contrast",
                    "duration": 5
                },
                {
                    "scene_number": 3,
                    "prompt": "Silhouette of the explorer walking forward and stepping directly into a bright shimmering portal of golden-blue light.",
                    "camera": "Tracking shot from behind the explorer, over-the-shoulder perspective",
                    "lighting": "Warm golden portal glow, cinematic backlighting, bright volumetric rays",
                    "duration": 5
                }
            ])
            shared_memory.write("showrunner", "scene_params", fallback)
            with open(os.path.join(workspace_dir, "scene_params.json"), "w", encoding="utf-8") as f:
                f.write(fallback)
            shared_memory.write("showrunner", "progress", "Scene Planner: 100% (Fallback)")
            return fallback
