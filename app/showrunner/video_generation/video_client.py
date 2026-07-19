"""Video API Client: Submits and monitors video generation jobs to Qwen Cloud / Wan Video API."""

from __future__ import annotations

import random
from typing import Dict, Any
from app.core.logger import get_logger

logger = get_logger("agentsphere.video.client")


class VideoGenerationClient:
    """Invokes async video generation endpoints and polls statuses."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or "mocked_qwen_dashscope_key"
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def submit_job(self, prompt: str, duration: int = 5) -> str:
        """Submit a text-to-video generation job and return a Job ID."""
        job_id = f"job_wan_{random.randint(100000, 999999)}"
        self._jobs[job_id] = {
            "prompt": prompt,
            "duration": duration,
            "status": "submitted",
            "progress": 0,
            "retry_count": 0
        }
        logger.info(f"Wan Video: Job '{job_id}' submitted successfully. Prompt: {prompt[:50]}...")
        return job_id

    def poll_status(self, job_id: str) -> Dict[str, Any]:
        """Poll the status and progress of a submitted job."""
        if job_id not in self._jobs:
            return {"status": "failed", "error": "Job not found", "progress": 0}

        job = self._jobs[job_id]
        
        # Simulate status progression
        if job["status"] == "submitted":
            job["status"] = "running"
            job["progress"] = 25
        elif job["status"] == "running":
            job["progress"] += 35
            if job["progress"] >= 100:
                job["status"] = "completed"
                job["progress"] = 100

        logger.info(f"Wan Video: Job '{job_id}' status: '{job['status']}' ({job['progress']}%)")
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "video_url": f"/static/output/scenes/{job_id}.mp4" if job["status"] == "completed" else None
        }
