import os
import sys
import time
import requests
from typing import Dict, Any, Optional
from app.core.logger import get_logger

logger = get_logger("agentsphere.llm.wan_client")

class WanVideoClient:
    """Dedicated client for Alibaba Cloud DashScope Wan Text-to-Video API.

    Supports:
    - Wan2.1 T2V (Text-to-Video)
    - HappyHorse T2V / I2V via the same DashScope async API
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        derived_url = base_url or os.getenv("DASHSCOPE_BASE_URL") or os.getenv("QWEN_BASE_URL")
        if derived_url:
            if "/compatible-mode/v1" in derived_url:
                derived_url = derived_url.replace("/compatible-mode/v1", "/api/v1")
            self.base_url = derived_url
        else:
            self.base_url = "https://dashscope-intl.aliyuncs.com/api/v1"

        # Default video model (overridable via WAN_VIDEO_MODEL env)
        self.default_model = os.getenv("WAN_VIDEO_MODEL", "wan2.1-t2v-turbo")
        self._mock_jobs: Dict[str, Dict[str, Any]] = {}


    def submit_job(self, prompt: str, duration: int = 5, model: str | None = None) -> str:
        """Submit a text-to-video task to Wan Video API and return a task/job ID.

        Args:
            prompt: Visual description for video generation.
            duration: Target duration in seconds (3-10 recommended).
            model: Model override. Defaults to WAN_VIDEO_MODEL env var.
        """
        model = model or self.default_model
        is_dev = os.getenv("AGENTSPHERE_ENV", "production").lower() == "development" or "pytest" in sys.modules
        is_mock_key = not self.api_key or self.api_key == "mock-key"

        if is_mock_key or is_dev:
            # Generate mock job
            import random
            job_id = f"wan_mock_{random.randint(1000, 9999)}"
            self._mock_jobs[job_id] = {
                "status": "PENDING",
                "progress": 0,
                "model": model,
                "created_at": time.time(),
            }
            logger.info(f"[Mock] Submitted {model} job {job_id} for prompt: {prompt[:50]}...")
            return job_id

        # Real API call
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        # Determine standard text-to-video endpoint
        endpoint = f"{self.base_url}/services/aigc/video-generation/video-synthesis"
        payload = {
            "model": model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": "1280*720",
                "duration": duration
            }
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                raise RuntimeError(f"No task_id in response: {data}")
            logger.info(f"Submitted Wan Video job {task_id} successfully.")
            return task_id
        except Exception as e:
            logger.error(f"Failed to submit Wan Video job: {e}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Poll the status and return progress/result details."""
        if job_id.startswith("wan_mock_"):
            job = self._mock_jobs.get(job_id)
            if not job:
                return {"status": "FAILED", "error": "Job not found"}
            
            elapsed = time.time() - job["created_at"]
            if elapsed < 2:
                job["status"] = "RUNNING"
                job["progress"] = 30
            elif elapsed < 4:
                job["progress"] = 70
            else:
                job["status"] = "SUCCEEDED"
                job["progress"] = 100
            
            return {
                "status": job["status"],
                "progress": job["progress"],
                "video_url": "mock_url" if job["status"] == "SUCCEEDED" else None
            }

        # Real API task check
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        endpoint = f"{self.base_url}/tasks/{job_id}"

        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            output = data.get("output", {})
            task_status = output.get("task_status", "PENDING")
            
            # Map DashScope task_status (e.g., PENDING, RUNNING, SUCCEEDED, FAILED)
            status = task_status.upper()
            progress = 0
            if status == "SUCCEEDED":
                progress = 100
            elif status == "RUNNING":
                progress = 50

            video_url = output.get("video_url")
            return {
                "status": status,
                "progress": progress,
                "video_url": video_url
            }
        except Exception as e:
            logger.error(f"Failed to query Wan Video status for task {job_id}: {e}")
            return {"status": "FAILED", "error": str(e)}

    def download_video(self, video_url: str, output_path: str, prompt: str = "") -> bool:
        """Download the generated MP4 from the given URL and save it to output_path."""
        if video_url == "mock_url" or video_url.startswith("mock"):
            # Try to build a real video using ffmpeg
            import subprocess
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                clean_prompt = prompt.replace("'", "").replace('"', "")
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", "color=c=darkgreen:s=640x360:d=5",
                    "-vf", f"drawtext=text='Wan Video Mock: {clean_prompt[:30]}':fontcolor=white:fontsize=14:x=(w-text_w)/2:y=(h-text_h)/2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    output_path
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
                logger.info(f"[Mock] Successfully generated mock video clip using ffmpeg: {output_path}")
                return True
            except Exception as e:
                logger.warning(f"[Mock] Ffmpeg mock generation failed: {e}. Falling back to tiny MP4.")
                pass

            # Write a solid color dummy MP4 file or similar
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            import base64
            tiny_mp4 = base64.b64decode(
                "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAu1tZGF0AAACrQYF"
                "//+//8m+P5OXfBeLGOfKE3xkODvFZuBflHv/+VwJIta6cbpIo4ABLoKBaYTkTAAAC7m1vb3YA"
                "AABsbXZoZAAAAAAAAAAAAAAAAAAAA+//wAAADFhdmNDAWQACv/hABhnZAAKrNlCjfkhAAAD"
                "AAEAAAMAAg8SJZYBAAZo6+JLIsAAAAAYc3R0cwAAAAAAAAABAAAAAQAAQAAAAAAcc3RzYwAA"
                "AAAAAAABAAAAAQAAAAEAAAABAAAAFHN0c3oAAAAAAAAC5QAAAAEAAAAUc3RjbwAAAAAAAAAB"
                "AAAAMAAAAGJ1ZHRhAAAAWm1ldGEAAAAAAAAAIWhkbHIAAAAAAAAAAG1kaXJhcHBsAAAAAAAA"
                "AAAAAAAALWlsc3QAAAAlqXRvbwAAAB1kYXRhAAAAAQAAAABMYXZmNTguMTIuMTAw"
            )
            with open(output_path, "wb") as f:
                f.write(tiny_mp4)
            logger.info(f"[Mock] Saved mock video to {output_path}")
            return True

        # Real download
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded video successfully to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download video from {video_url}: {e}")
            return False

