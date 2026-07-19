"""Video Service — orchestrates WanVideoClient / HappyHorse for scene video generation.

Architecture:
    showrunner_video plugin
          │
          ▼
    VideoService          ← this module
          │
          ▼
    WanVideoClient  ──►  DashScope API (Wan2.1-T2V / HappyHorse-T2V)
          │
          ▼
    video_url / local file

Usage:
    from app.services.video_service import VideoService

    svc = VideoService()
    job_id = svc.submit(prompt="Futuristic city skyline at dusk", duration=5)
    result = svc.wait_for_result(job_id)
    # result = {"status": "SUCCEEDED", "video_url": "...", "local_path": "..."}
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger("agentsphere.services.video")


class VideoService:
    """High-level video generation service wrapping WanVideoClient.

    Supports:
    - Text-to-Video (Wan2.1-T2V, HappyHorse-T2V)
    - Image-to-Video (HappyHorse-I2V) when image_url is provided
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        from app.llm.wan_client import WanVideoClient

        self.model = model or settings.wan_video_model
        self._client = WanVideoClient(api_key=api_key)
        logger.info(f"[VideoService] Initialized with model: {self.model}")

    def submit(self, prompt: str, duration: int = 5, model: Optional[str] = None) -> str:
        """Submit a text-to-video generation job.

        Args:
            prompt:   Visual scene description.
            duration: Target duration in seconds (3–10).
            model:    Override model (e.g., ``happyHorse-T2V``).

        Returns:
            Job ID string for polling.
        """
        active_model = model or self.model
        logger.info(f"[VideoService] Submitting T2V job — model={active_model}, prompt={prompt[:60]}...")
        job_id = self._client.submit_job(prompt, duration=duration, model=active_model)
        logger.info(f"[VideoService] Job submitted: {job_id}")
        return job_id

    def poll(self, job_id: str) -> Dict[str, Any]:
        """Check the current status of a submitted video job.

        Returns:
            Dict with keys: ``status`` (PENDING/RUNNING/SUCCEEDED/FAILED),
            ``progress`` (0-100), ``video_url`` (when completed).
        """
        return self._client.get_job_status(job_id)

    def wait_for_result(
        self,
        job_id: str,
        output_path: Optional[str] = None,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> Dict[str, Any]:
        """Poll until the job completes, then optionally download the video.

        Args:
            job_id:        Job ID returned by :meth:`submit`.
            output_path:   If provided, the video will be downloaded here.
            poll_interval: Seconds between status checks.
            max_wait:      Maximum total wait time in seconds.

        Returns:
            Dict with ``status``, ``video_url``, and optionally ``local_path``.
        """
        start = time.time()
        while True:
            status_info = self.poll(job_id)
            status = status_info.get("status", "PENDING")
            progress = status_info.get("progress", 0)

            logger.info(f"[VideoService] Job {job_id}: {status} ({progress}%)")

            if status == "SUCCEEDED":
                video_url = status_info.get("video_url")
                result: Dict[str, Any] = {"status": "SUCCEEDED", "video_url": video_url}

                if output_path and video_url:
                    prompt_hint = status_info.get("prompt", "")
                    downloaded = self._client.download_video(video_url, output_path, prompt=prompt_hint)
                    if downloaded:
                        result["local_path"] = output_path
                        logger.info(f"[VideoService] Downloaded to {output_path}")

                return result

            if status == "FAILED":
                error = status_info.get("error", "Unknown error")
                logger.error(f"[VideoService] Job {job_id} failed: {error}")
                return {"status": "FAILED", "error": error}

            elapsed = time.time() - start
            if elapsed > max_wait:
                logger.error(f"[VideoService] Job {job_id} timed out after {max_wait}s")
                return {"status": "FAILED", "error": f"Timeout after {max_wait}s"}

            time.sleep(poll_interval)

    def generate_scene(
        self,
        prompt: str,
        output_path: str,
        duration: int = 5,
        model: Optional[str] = None,
    ) -> str:
        """One-shot helper: submit → wait → download → return local path.

        Args:
            prompt:      Visual scene description for the video.
            output_path: Where to save the generated MP4.
            duration:    Target duration in seconds.
            model:       Model override (e.g., ``happyHorse-T2V``).

        Returns:
            Local file path of the downloaded video.

        Raises:
            RuntimeError: If video generation fails.
        """
        job_id = self.submit(prompt, duration=duration, model=model)
        result = self.wait_for_result(job_id, output_path=output_path)

        if result["status"] != "SUCCEEDED":
            raise RuntimeError(f"Video generation failed: {result.get('error')}")

        return result.get("local_path", output_path)

    @property
    def active_model(self) -> str:
        """Return the currently configured video model name."""
        return self.model
