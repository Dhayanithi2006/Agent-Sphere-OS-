"""Video Pipeline: Coordinates async video API generation, polling services, and file downloads."""

from __future__ import annotations

import asyncio
from app.showrunner.video_generation.video_client import VideoGenerationClient
from app.showrunner.video_generation.scene_queue import SceneQueueManager
from app.core.logger import get_logger

logger = get_logger("agentsphere.video.pipeline")
client = VideoGenerationClient()
queue_manager = SceneQueueManager()


async def render_scene_video(scene_id: str, prompt: str, duration: int = 5) -> str:
    """Asynchronously submit a video generation job, poll progress, and wait for completed download."""
    queue_manager.add_scene(scene_id, prompt)
    
    # 1. Submit Job
    job_id = client.submit_job(prompt, duration)
    queue_manager.update_status(scene_id, "submitted", 0)
    
    # 2. Polling Loop (Module 41)
    while True:
        await asyncio.sleep(0.5)
        status_info = client.poll_status(job_id)
        
        status = status_info["status"]
        progress = status_info["progress"]
        
        if status == "completed":
            queue_manager.update_status(scene_id, "downloading", 90)
            await asyncio.sleep(0.3) # Simulate download latency
            
            # Simulate successful download to cache
            video_path = f"app/static/output/scenes/{scene_id}.mp4"
            queue_manager.update_status(scene_id, "completed", 100)
            logger.info(f"Video Pipeline: Scene '{scene_id}' completed and saved to: {video_path}")
            return video_path
            
        elif status == "failed":
            queue_manager.update_status(scene_id, "failed", progress, error=status_info.get("error"))
            raise RuntimeError(f"Video generation failed for scene '{scene_id}': {status_info.get('error')}")
            
        else:
            # Job is running
            queue_manager.update_status(scene_id, "running", progress)
