"""Integration tests for the AI Showrunner pipeline agents."""

from __future__ import annotations

import os
import json
import pytest
from app.core.shared import kernel, supervisor, shared_memory
from app.models.task import TaskStatus


@pytest.fixture(autouse=True)
async def setup_microkernel():
    """Ensure microkernel is booted and showrunner agents are registered before running tests."""
    if not kernel.is_booted:
        await kernel.boot()
    yield


@pytest.mark.anyio
async def test_showrunner_agents_registered():
    """Verify that all 10 showrunner agents are loaded and registered with the supervisor."""
    expected_agents = [
        "showrunner_planner",
        "showrunner_script",
        "showrunner_storyboard",
        "showrunner_scene",
        "showrunner_prompt",
        "showrunner_video",
        "showrunner_audio",
        "showrunner_subtitle",
        "showrunner_editor",
        "showrunner_reviewer",
    ]
    for agent_id in expected_agents:
        assert agent_id in supervisor._agents
        assert supervisor._agents[agent_id] is not None


@pytest.mark.anyio
async def test_showrunner_end_to_end_pipeline():
    """Run the entire AI Movie Production pipeline end-to-end and check outputs."""
    # Reset shared memory state
    shared_memory.delete("showrunner:movie_goal")
    shared_memory.delete("showrunner:scenes")
    shared_memory.delete("showrunner:script")
    shared_memory.delete("showrunner:storyboard")
    shared_memory.delete("showrunner:scene_params")
    shared_memory.delete("showrunner:optimized_prompts")
    shared_memory.delete("showrunner:video_clips")
    shared_memory.delete("showrunner:audio_clips")
    shared_memory.delete("showrunner:music_clip")
    shared_memory.delete("showrunner:final_movie")
    shared_memory.delete("showrunner:approval_state")

    movie_goal = "A futuristic city space battle commercial"
    
    # 1. Run Planner
    task_id = await supervisor.submit_task("Planner Run", "showrunner_planner", {"movie_goal": movie_goal})
    res = await supervisor.run_task(task_id)
    assert res.success is True
    scenes_data = json.loads(res.output)
    scenes = scenes_data.get("scenes", scenes_data) if isinstance(scenes_data, dict) else scenes_data
    assert len(scenes) == 3
    assert scenes[0]["scene_number"] == 1

    # 2. Run Script Agent
    task_id = await supervisor.submit_task("Script Run", "showrunner_script")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    script_data = json.loads(res.output)
    script_scenes = script_data.get("scenes", script_data) if isinstance(script_data, dict) else script_data
    assert len(script_scenes) == 3
    assert "camera_notes" in script_scenes[0] or "visual_action" in script_scenes[0]

    # 3. Run Storyboard Agent
    task_id = await supervisor.submit_task("Storyboard Run", "showrunner_storyboard")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    storyboard = json.loads(res.output)
    assert len(storyboard) == 3
    assert shared_memory.read("showrunner", "approval_state") == "pending"

    # Simulate Human-in-the-loop Storyboard Approval
    shared_memory.write("showrunner", "approval_state", "approved")

    # 4. Run Scene Agent
    task_id = await supervisor.submit_task("Scene Planner Run", "showrunner_scene")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    scene_params = json.loads(res.output)
    assert len(scene_params) == 3
    assert "duration" in scene_params[0]

    # 5. Run Prompt Agent
    task_id = await supervisor.submit_task("Prompt Opt Run", "showrunner_prompt")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    opt_prompts = json.loads(res.output)
    assert len(opt_prompts) == 3
    assert "8k" in opt_prompts[0]["prompt"] or "photorealistic" in opt_prompts[0]["prompt"] or "cinematic" in opt_prompts[0]["prompt"]

    # 6. Run Video Agent
    task_id = await supervisor.submit_task("Video Render Run", "showrunner_video")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    video_clips = json.loads(res.output)
    assert len(video_clips) == 3
    assert os.path.exists(video_clips[0])

    # 7. Run Audio Agent
    task_id = await supervisor.submit_task("Audio Gen Run", "showrunner_audio")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    audio_info = json.loads(res.output)
    assert len(audio_info["audio_clips"]) == 3
    assert os.path.exists(audio_info["music_clip"])

    # 8. Run Subtitle Agent
    task_id = await supervisor.submit_task("Subtitles Gen Run", "showrunner_subtitle")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    assert os.path.exists(res.output)

    # 9. Run Editor Agent
    task_id = await supervisor.submit_task("Editor Compile Run", "showrunner_editor")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    assert os.path.exists(res.output)
    assert res.output.endswith("movie.mp4")

    # 10. Run Reviewer Agent
    task_id = await supervisor.submit_task("Release Review Run", "showrunner_reviewer")
    res = await supervisor.run_task(task_id)
    assert res.success is True
    assert "APPROVED" in res.output or "Approved" in res.output or "release" in res.output.lower()
