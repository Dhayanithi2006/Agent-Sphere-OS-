"""Prompt optimizer agent for the AI Showrunner pipeline."""

from __future__ import annotations

import os
import json
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory


class ShowrunnerPromptAgent(BaseAgent):
    """Prompt Agent: Enhances and expands basic scene prompts with cinematic stylistic tags."""

    def __init__(self, agent_id: str = "showrunner_prompt", name: str = "showrunner_prompt") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Prompt Optimizer")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Prompt Optimizer Agent")
        
        # 1. Fetch scene params
        params_json = shared_memory.read("showrunner", "scene_params")
        if not params_json:
            raise ValueError("No scene parameters found in shared memory. Ensure Scene Agent runs first.")

        # Retrieve task pid for workspace
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        shared_memory.write("showrunner", "progress", "Prompt Optimizer: 50% (Refining Prompts...)")

        # 2. Call Model Router using 'prompt' task type (routes to qwen-plus)
        prompt = (
            "You are a cinematic prompt engineer. Optimize the basic prompt for each scene to make it visually spectacular "
            "when sent to a state-of-the-art video generator (like Wan Video). "
            f"Scene Parameters:\n{params_json}\n\n"
            "For each scene, enhance the 'prompt' field with high-quality descriptors (e.g. photorealistic, 8k resolution, "
            "unreal engine 5 style, hyper-detailed, raytracing, cinematic lighting). Keep all other fields ('scene_number', 'camera', 'lighting', 'duration') unchanged. "
            "Format your response as a JSON array of scene parameters. Example format:\n"
            '[{"scene_number": 1, "prompt": "photorealistic, cinematic, ...", "camera": "...", "lighting": "...", "duration": 5}]\n'
            "Return ONLY raw JSON."
        )

        try:
            response = model_router.generate(prompt, "prompt")
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()

            json.loads(response_clean)

            shared_memory.write("showrunner", "optimized_prompts", response_clean)
            
            # Save to workspace
            with open(os.path.join(workspace_dir, "optimized_prompts.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)

            shared_memory.write("showrunner", "progress", "Prompt Optimizer: 100% (Completed)")
            return response_clean
        except Exception as e:
            self.logger.warning(f"Prompt agent failed: {e}")
            fallback = json.dumps([
                {
                    "scene_number": 1,
                    "prompt": "An explorer standing on a dark forest path looking down at a bright glowing blue crystal on the floor. Photorealistic, 8k resolution, hyper-detailed textures, cinematic lighting, volumetric mist, mystery vibe.",
                    "camera": "Slow zoom in, low-angle shot, cinematic slide",
                    "lighting": "Volumetric cyan glow, dim ambient forest light, high contrast",
                    "duration": 5
                },
                {
                    "scene_number": 2,
                    "prompt": "A glowing holographic city grid map rising out of the blue crystal inside the forest, explorer with amazed expression. Pinks, purples, neon lines, cybernetic details, Unreal Engine 5 render, cinematic raytracing.",
                    "camera": "Static low-angle shot, looking up from the crystal",
                    "lighting": "Vibrant glowing pink and purple neon hologram lines, high contrast",
                    "duration": 5
                },
                {
                    "scene_number": 3,
                    "prompt": "Silhouette of the explorer walking forward and stepping directly into a bright shimmering portal of golden-blue light. Volumetric rays, anamorphic lens flare, high end commercial style, dramatic transitions.",
                    "camera": "Tracking shot from behind the explorer, over-the-shoulder perspective",
                    "lighting": "Warm golden portal glow, cinematic backlighting, bright volumetric rays",
                    "duration": 5
                }
            ])
            shared_memory.write("showrunner", "optimized_prompts", fallback)
            with open(os.path.join(workspace_dir, "optimized_prompts.json"), "w", encoding="utf-8") as f:
                f.write(fallback)
            shared_memory.write("showrunner", "progress", "Prompt Optimizer: 100% (Fallback)")
            return fallback
