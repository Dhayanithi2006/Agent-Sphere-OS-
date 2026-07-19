"""Multi-Workflow Engine executing customizable DAG steps for different media forms."""

from __future__ import annotations

import asyncio
from typing import Callable, List, Dict, Any
from app.core.shared import supervisor, shared_memory, recovery_engine


class WorkflowEngine:
    """Manages and executes specialized agent DAG pathways based on selected media types."""

    WORKFLOWS = {
        "movie": [
            ("showrunner_planner", "Planner Task", "Planner"),
            # Parallel block run inside pipeline runner
            ("showrunner_parallel", "Parallel Task", "Parallel Setup"),
            ("showrunner_director", "Director Task", "Cinematic Director"),
            ("showrunner_scene", "Scene Planner Task", "Scene Planner"),
            ("showrunner_prompt", "Prompt Optimizer Task", "Prompt Optimizer"),
            ("showrunner_video", "Video Generator Task", "Video Generator"),
            ("showrunner_audio", "Audio Generator Task", "Audio Generator"),
            ("showrunner_subtitle", "Subtitle Generator Task", "Subtitle Generator"),
            ("showrunner_editor", "Video Editor Task", "Video Editor"),
            ("showrunner_poster", "Poster Task", "Poster Generator"),
            ("showrunner_trailer", "Trailer Task", "Trailer Splicer"),
            ("showrunner_publisher", "Publish Task", "Publishing Agent"),
            ("showrunner_reviewer", "QA Review Task", "Reviewer"),
            ("showrunner_reporter", "Report Task", "Production Reporter")
        ],
        "podcast": [
            ("showrunner_researcher", "Brand Research", "Researcher"),
            ("showrunner_script", "Script Task", "Script"),
            ("showrunner_voice", "Voice Selection", "Voice selector"),
            ("showrunner_audio", "Audio Generator Task", "Audio Generator"),
            ("showrunner_reviewer", "QA Review Task", "Reviewer")
        ],
        "advertisement": [
            ("showrunner_researcher", "Brand Research", "Researcher"),
            ("showrunner_script", "Script Task", "Script"),
            ("showrunner_storyboard", "Storyboard Task", "Storyboard"),
            ("showrunner_video", "Video Generator Task", "Video Generator"),
            ("showrunner_audio", "Audio Generator Task", "Audio Generator"),
            ("showrunner_editor", "Video Editor Task", "Video Editor"),
            ("showrunner_reviewer", "QA Review Task", "Reviewer")
        ],
        "game trailer": [
            ("showrunner_planner", "Planner Task", "Planner"),
            ("showrunner_script", "Script Task", "Script"),
            ("showrunner_storyboard", "Storyboard Task", "Storyboard"),
            ("showrunner_video", "Video Generator Task", "Video Generator"),
            ("showrunner_audio", "Audio Generator Task", "Audio Generator"),
            ("showrunner_editor", "Video Editor Task", "Video Editor"),
            ("showrunner_reviewer", "QA Review Task", "Reviewer")
        ],
        "music video": [
            ("showrunner_planner", "Planner Task", "Planner"),
            ("showrunner_storyboard", "Storyboard Task", "Storyboard"),
            ("showrunner_video", "Video Generator Task", "Video Generator"),
            ("showrunner_audio", "Audio Generator Task", "Audio Generator"),
            ("showrunner_editor", "Video Editor Task", "Video Editor"),
            ("showrunner_reviewer", "QA Review Task", "Reviewer")
        ],
        "documentary": [
            ("showrunner_researcher", "Brand Research", "Researcher"),
            ("showrunner_script", "Script Task", "Script"),
            ("showrunner_audio", "Audio Generator Task", "Audio Generator"),
            ("showrunner_video", "Video Generator Task", "Video Generator"),
            ("showrunner_subtitle", "Subtitle Generator Task", "Subtitle Generator"),
            ("showrunner_editor", "Video Editor Task", "Video Editor"),
            ("showrunner_reviewer", "QA Review Task", "Reviewer")
        ]
    }

    @classmethod
    def get_steps(cls, workflow_type: str) -> List[tuple[str, str, str]]:
        """Return steps for a given media workflow."""
        normalized = str(workflow_type).lower().strip()
        if normalized not in cls.WORKFLOWS:
            # Default to Movie pipeline
            return cls.WORKFLOWS["movie"]
        return cls.WORKFLOWS[normalized]
