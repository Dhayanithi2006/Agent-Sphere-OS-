"""Subtitle generator agent for the AI Showrunner pipeline."""

from __future__ import annotations

import os
import json
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import shared_memory


class ShowrunnerSubtitleAgent(BaseAgent):
    """Subtitle Agent: Generates SRT subtitles synced to scene timing."""

    def __init__(self, agent_id: str = "showrunner_subtitle", name: str = "showrunner_subtitle") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Subtitle Generator")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Subtitle Generator Agent")

        # 1. Fetch script
        script_json = shared_memory.read("showrunner", "script")
        if not script_json:
            raise ValueError("No script found in shared memory. Ensure Script Agent runs first.")

        scenes_data = json.loads(script_json)
        scenes_list = scenes_data.get("scenes", scenes_data) if isinstance(scenes_data, dict) else scenes_data

        # Retrieve task pid for workspace
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)

        static_dir = os.path.join("app", "static", "output")
        os.makedirs(static_dir, exist_ok=True)

        srt_path = os.path.join(static_dir, "subtitles.srt")
        workspace_srt_path = os.path.join(workspace_dir, "subtitle.srt")
        
        shared_memory.write("showrunner", "progress", "Subtitle: 50% (Aligning text timings...)")

        import subprocess

        def get_audio_duration(file_path: str, fallback_text: str) -> float:
            if os.path.exists(file_path):
                try:
                    cmd = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", file_path
                    ]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=5)
                    dur = float(result.stdout.strip())
                    if dur > 0.1:
                        return dur
                except Exception:
                    pass
            # word count fallback
            words = len(fallback_text.split())
            if words > 0:
                return max(3.0, round(words / 2.5, 1))
            return 5.0

        def format_srt_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds - int(seconds)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        # 2. Build SRT structure
        srt_content = ""
        current_time = 0.0

        for i, scene in enumerate(scenes_list):
            scene_num = scene.get("scene_number", i + 1)
            narration = scene.get("narration", "")
            
            dialogue_items = scene.get("dialogues", [])
            if dialogue_items and isinstance(dialogue_items, list):
                dialogue = " ".join([f"{d.get('character', 'Unknown')}: {d.get('text', '')}" for d in dialogue_items])
                text_to_measure = " ".join([d.get('text', '') for d in dialogue_items])
            else:
                dialogue = scene.get("dialogue", "")
                text_to_measure = dialogue or narration or ""
            
            voice_file = os.path.join(static_dir, f"scene_{scene_num:02d}_voice.mp3")
            dur = get_audio_duration(voice_file, text_to_measure)
            
            start_str = format_srt_time(current_time)
            end_str = format_srt_time(current_time + dur)

            srt_content += f"{scene_num}\n"
            srt_content += f"{start_str} --> {end_str}\n"
            
            text_lines = []
            if narration:
                text_lines.append(f"Narrator: {narration}")
            if dialogue:
                text_lines.append(dialogue)
                
            srt_content += "\n".join(text_lines) + "\n\n"
            current_time += dur

        # 3. Write files
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        with open(workspace_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        shared_memory.write("showrunner", "subtitles_file", srt_path)
        shared_memory.write("showrunner", "progress", "Subtitle: 100% (Completed)")

        return workspace_srt_path
