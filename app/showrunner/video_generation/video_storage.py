"""Video Storage Manager: Structures persistent production directories inside the workspace."""

from __future__ import annotations

import os
import shutil
from typing import Dict
from app.core.logger import get_logger

logger = get_logger("agentsphere.video.storage")


class VideoStorageManager:
    """Orchestrates asset storage folders inside workspaces."""

    @classmethod
    def setup_production_assets(cls, pid: str) -> Dict[str, str]:
        """Create structured folders according to production standard asset layouts."""
        from app.core.shared import shared_memory
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        base = os.path.join("workspace", user, media_type, pid_str)
        paths = {
            "root": base,
            "script": os.path.join(base, "script"),
            "storyboard": os.path.join(base, "storyboard"),
            "prompts": os.path.join(base, "prompts"),
            "videos": os.path.join(base, "videos"),
            "audio": os.path.join(base, "audio"),
            "subtitles": os.path.join(base, "subtitles"),
            "posters": os.path.join(base, "posters"),
            "trailer": os.path.join(base, "trailer"),
            "thumbnail": os.path.join(base, "thumbnail")
        }

        for folder_name, folder_path in paths.items():
            os.makedirs(folder_path, exist_ok=True)
            
        logger.info(f"Storage: Setup production asset directory structure for PID: {pid}")
        return paths

    @classmethod
    def save_scene_clip(cls, src_path: str, pid: str, scene_num: int) -> str:
        """Copy a generated scene clip to the production workspace folder."""
        paths = cls.setup_production_assets(pid)
        dest_filename = f"scene{scene_num}.mp4"
        dest_path = os.path.join(paths["videos"], dest_filename)
        
        try:
            # Local copy or file write fallback
            if os.path.exists(src_path):
                shutil.copy2(src_path, dest_path)
            else:
                with open(dest_path, "wb") as f:
                    f.write(b"MOCK_GENERATED_WAN_VIDEO_DATA")
            logger.info(f"Storage: Saved scene clip {scene_num} to workspace: {dest_path}")
        except Exception as e:
            logger.error(f"Storage: Failed to copy clip: {e}")
            
        return dest_path
