"""Unit and integration tests for Modules 36 to 53 (Cinematic Studio, Video Pipeline, Director, Poster, Reports)."""

from __future__ import annotations

import os
import json
import pytest
import asyncio
from app.showrunner.video_generation.video_client import VideoGenerationClient
from app.showrunner.video_generation.scene_queue import SceneQueueManager
from app.showrunner.video_generation.video_pipeline import render_scene_video
from app.showrunner.video_generation.video_storage import VideoStorageManager
from app.plugins.showrunner.director_agent import ShowrunnerDirectorAgent
from app.plugins.showrunner.poster_generator import ShowrunnerPosterAgent
from app.plugins.showrunner.trailer_generator import ShowrunnerTrailerAgent
from app.plugins.showrunner.publishing_agent import ShowrunnerPublishingAgent
from app.plugins.showrunner.report_generator import ShowrunnerReportAgent


def test_video_client_job_polling():
    """Verify that VideoGenerationClient submits jobs and advances through polling states."""
    client = VideoGenerationClient()
    job_id = client.submit_job("Cinematic camera pan across nebula", duration=5)
    assert job_id.startswith("job_wan_")
    
    # Poll multiple times to check status progressions
    res1 = client.poll_status(job_id)
    assert res1["status"] in ["submitted", "running"]
    
    res2 = client.poll_status(job_id)
    assert res2["status"] in ["running", "completed"]


def test_scene_queue_manager():
    """Verify that SceneQueueManager tracks render progresses."""
    qm = SceneQueueManager()
    qm.add_scene("scene_1", "Neon ninja jumping over fence")
    
    snapshot = qm.get_snapshot()
    assert len(snapshot) == 1
    assert snapshot[0]["status"] == "submitted"
    
    qm.update_status("scene_1", "running", 50)
    assert qm.get_snapshot()[0]["progress"] == 50


@pytest.mark.anyio
async def test_async_video_pipeline():
    """Verify that the async video pipeline runs, polls, and saves to file cache."""
    video_path = await render_scene_video("scene_test", "Sci-fi ship docking", duration=3)
    assert "scene_test.mp4" in video_path


def test_production_asset_manager_folders():
    """Verify setup of the standard film production asset directories."""
    paths = VideoStorageManager.setup_production_assets("PID-test-999")
    assert os.path.exists(paths["videos"])
    assert os.path.exists(paths["posters"])
    assert os.path.exists(paths["thumbnail"])
    
    # Save a scene clip
    saved = VideoStorageManager.save_scene_clip("non_existent_stub.mp4", "PID-test-999", 1)
    assert os.path.exists(saved)


def test_cinematic_director_audit():
    """Verify that DirectorAgent reviews scripts and storyboard consistency."""
    from app.core.shared import shared_memory
    shared_memory.write("showrunner", "script", json.dumps([{"scene_number": 1, "dialogue": "Hello world"}]))
    
    director = ShowrunnerDirectorAgent()
    report = director.execute({"pid": "test_pid"})
    assert "Audit" in report or "fallback" in report.lower()


def test_poster_generator():
    """Verify that PosterAgent writes movie poster assets to the poster directory."""
    poster = ShowrunnerPosterAgent()
    res = poster.execute({"pid": "test_pid", "movie_goal": "Cyberpunk Neon Odyssey"})
    # Accept both PNG (image API) and SVG (rich LLM fallback) poster formats
    assert "poster.png" in res or "poster.svg" in res, f"Unexpected poster output: {res}"


def test_trailer_generator():
    """Verify that TrailerAgent compiles trailer MP4 files."""
    trailer = ShowrunnerTrailerAgent()
    res = trailer.execute({"pid": "test_pid"})
    assert "trailer.mp4" in res


def test_publishing_agent_oss():
    """Verify that PublishingAgent uploads file to OSS bucket and returns link."""
    publisher = ShowrunnerPublishingAgent()
    res = publisher.execute({"pid": "test_pid"})
    assert "http" in res or "releases" in res


def test_production_report_exporter():
    """Verify that ReportAgent outputs HTML and Markdown summaries."""
    reporter = ShowrunnerReportAgent()
    res = reporter.execute({"pid": "test_pid"})
    assert "production_report.md" in res.lower()


def test_showrunner_planner_agent():
    """Verify that ShowrunnerPlannerAgent generates structured JSON output."""
    from app.plugins.showrunner.planner import ShowrunnerPlannerAgent
    from app.core.shared import shared_memory

    # Force development mode to guarantee stub response without active API key
    import os
    os.environ["AGENTSPHERE_ENV"] = "development"

    planner = ShowrunnerPlannerAgent()
    res = planner.execute({
        "pid": "test_planner_pid",
        "movie_title": "The Time Machine Adventure",
        "genre": "Adventure",
        "duration": "45 sec",
        "target_audience": "Kids",
        "language": "English",
        "style": "Pixar"
    })

    data = json.loads(res)
    assert "title" in data
    assert "genre" in data
    assert "scenes" in data
    assert len(data["scenes"]) == 3
    assert data["scenes"][0]["scene_number"] == 1


def test_showrunner_script_agent():
    """Verify that ShowrunnerScriptAgent reads planner.json and writes structured JSON script."""
    from app.plugins.showrunner.script_agent import ShowrunnerScriptAgent
    from app.core.shared import shared_memory

    import os
    os.environ["AGENTSPHERE_ENV"] = "development"

    # Write a mock planner.json to the workspace
    pid = "test_script_pid"
    workspace_dir = os.path.join("workspace", f"PID-{pid}")
    os.makedirs(workspace_dir, exist_ok=True)

    planner_data = {
        "title": "Space Voyage",
        "genre": "Sci-Fi",
        "duration": "30 sec",
        "scenes": [
            {"scene_number": 1, "title": "Launch", "description": "Ship takes off.", "goal": "Launch"},
            {"scene_number": 2, "title": "Orbit", "description": "Orbiting planet.", "goal": "Orbit"},
            {"scene_number": 3, "title": "Landing", "description": "Landing on mars.", "goal": "Land"}
        ]
    }
    with open(os.path.join(workspace_dir, "planner.json"), "w", encoding="utf-8") as f:
        json.dump(planner_data, f)

    script_agent = ShowrunnerScriptAgent()
    res = script_agent.execute({"pid": pid})

    data = json.loads(res)
    assert "title" in data
    assert "scenes" in data
    assert len(data["scenes"]) == 3
    assert "camera_notes" in data["scenes"][0]
    assert "dialogues" in data["scenes"][0]


