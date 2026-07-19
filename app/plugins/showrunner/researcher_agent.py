"""Research agent for the AI Showrunner pipeline."""

from __future__ import annotations

import json
import os
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory


class ShowrunnerResearchAgent(BaseAgent):
    """Research Agent: Performs target audience, tone, and keyword optimization."""

    def __init__(self, agent_id: str = "showrunner_researcher", name: str = "showrunner_researcher") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Research Agent")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Research Agent")

        movie_goal = (payload or {}).get("task") or (payload or {}).get("movie_goal") or ""
        if not movie_goal:
            movie_goal = shared_memory.read("showrunner", "movie_goal") or "A default story about AI"

        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        # Check semantic cache
        cached = shared_memory.read("cache", f"research:{movie_goal}")
        if cached:
            self.logger.info("Semantic cache hit for Research Agent!")
            shared_memory.write("showrunner", "brand_research", cached)
            # Write to workspace
            with open(os.path.join(workspace_dir, "research.json"), "w", encoding="utf-8") as f:
                f.write(cached)
            shared_memory.write("showrunner", "progress", "Research: 100% (Cache Hit)")
            return cached

        shared_memory.write("showrunner", "progress", "Research: 40% (Auditing target market...)")

        prompt = (
            "You are a media research specialist. Analyze the target audience and optimal visual tone for this film project. "
            f"Movie Goal: {movie_goal}\n\n"
            "Identify:\n"
            "1. 3-4 target audience keywords\n"
            "2. Optimal visual tone/theme keywords\n"
            "3. Projected audience appeal metrics.\n"
            "Format your response as a JSON object with: 'keywords', 'target_audience', 'theme_tone', and 'appeal_score'. "
            "Return ONLY raw JSON. Do not include markdown code block styling or any commentary."
        )

        try:
            response = model_router.generate(prompt, task_type="researcher")
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()

            # Validate JSON
            json.loads(response_clean)

            shared_memory.write("showrunner", "brand_research", response_clean)
            shared_memory.write("cache", f"research:{movie_goal}", response_clean)
            
            # Save to workspace
            with open(os.path.join(workspace_dir, "research.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)

            shared_memory.write("showrunner", "progress", "Research: 100% (Completed)")
            return response_clean
        except Exception as e:
            self.logger.warning(f"Research agent failed: {e}")
            fallback = json.dumps({
                "keywords": ["futuristic", "eco-friendly", "innovative"],
                "target_audience": "Tech enthusiasts & early adopters",
                "theme_tone": "Optimistic Sci-Fi with deep blue/green visuals",
                "appeal_score": 92
            })
            shared_memory.write("showrunner", "brand_research", fallback)
            with open(os.path.join(workspace_dir, "research.json"), "w", encoding="utf-8") as f:
                f.write(fallback)
            shared_memory.write("showrunner", "progress", "Research: 100% (Fallback)")
            return fallback
