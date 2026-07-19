"""Storyboard agent for the AI Showrunner pipeline."""

from __future__ import annotations

import os
import json
from typing import Any
from app.agents.base_agent import BaseAgent
from app.core.shared import model_router, shared_memory


class ShowrunnerStoryboardAgent(BaseAgent):
    """Storyboard Agent: Formulates composition panels and sets up the human-in-the-loop gate."""

    def __init__(self, agent_id: str = "showrunner_storyboard", name: str = "showrunner_storyboard") -> None:
        super().__init__(agent_id=agent_id, name=name, description="AI Showrunner Storyboard Generator")

    def execute(self, payload: dict[str, Any] | None = None) -> str:
        self.logger.info("Executing Showrunner Storyboard Agent")
        
        # 1. Fetch script
        script_json = shared_memory.read("showrunner", "script")
        if not script_json:
            raise ValueError("No script found in shared memory. Ensure Script Agent runs first.")

        # Retrieve task pid for workspace
        pid = shared_memory.read("showrunner", "current_pid") or (payload or {}).get("pid", "default_pid")
        user = shared_memory.read("showrunner", "user") or "default_user"
        media_type = shared_memory.read("showrunner", "type") or "default_type"
        pid_str = pid if str(pid).startswith("PID-") else f"PID-{pid}"
        
        workspace_dir = os.path.join("workspace", user, media_type, pid_str)
        os.makedirs(workspace_dir, exist_ok=True)
        storyboard_dir = os.path.join(workspace_dir, "storyboard")
        os.makedirs(storyboard_dir, exist_ok=True)

        static_storyboard_dir = os.path.join("app", "static", "output", user, media_type, pid_str, "storyboard")
        os.makedirs(static_storyboard_dir, exist_ok=True)

        # Function to generate valid PNG without dependencies
        import struct
        import zlib
        import subprocess
        
        def generate_solid_png(r: int, g: int, b: int) -> bytes:
            png_sig = b'\x89PNG\r\n\x1a\n'
            ihdr_data = struct.pack('>IIBBBBB', 128, 128, 8, 2, 0, 0, 0)
            def chunk(tag: bytes, data: bytes) -> bytes:
                return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
            row = b'\x00' + bytes([r, g, b]) * 128
            img_data = row * 128
            idat_data = zlib.compress(img_data)
            return png_sig + chunk(b'IHDR', ihdr_data) + chunk(b'IDAT', idat_data) + chunk(b'IEND', b'')

        def generate_storyboard_image(scene_num: int, composition: str, colors_str: str, desc: str, output_path: str):
            text = f"Scene {scene_num}\\nComp: {composition[:35]}\\nColors: {colors_str[:35]}\\nDesc: {desc[:40]}"
            escaped_text = text.replace("'", "").replace('"', "").replace(":", "\\:")
            color_map = {1: "darkgreen", 2: "purple", 3: "gold"}
            canvas_color = color_map.get(scene_num, "blue")
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c={canvas_color}:s=480x270:d=1",
                "-vf", f"drawtext=text='{escaped_text}':fontcolor=white:fontsize=16:x=(w-text_w)/2:y=(h-text_h)/2",
                "-vframes", "1",
                output_path
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except Exception:
                color_rgbs = {1: (0, 100, 0), 2: (128, 0, 128), 3: (218, 165, 32)}
                rgb = color_rgbs.get(scene_num, (0, 0, 255))
                with open(output_path, "wb") as f:
                    f.write(generate_solid_png(*rgb))

        # 2. Check cache
        movie_goal = shared_memory.read("showrunner", "movie_goal") or ""
        cached_storyboard = shared_memory.read("cache", f"storyboard:{movie_goal}:{user}")
        if cached_storyboard:
            self.logger.info("Semantic cache hit for Storyboard Agent!")
            panels = json.loads(cached_storyboard)
            for i, panel in enumerate(panels):
                scene_num = panel.get("scene_number", i + 1)
                comp = panel.get("composition", "Close-up")
                col = panel.get("colors", "Moody colors")
                desc = panel.get("description", "Preview panel")
                
                filename = f"scene{scene_num}.png"
                ws_path = os.path.join(storyboard_dir, filename)
                static_path = os.path.join(static_storyboard_dir, filename)
                
                generate_storyboard_image(scene_num, comp, col, desc, static_path)
                generate_storyboard_image(scene_num, comp, col, desc, ws_path)
                panel["image_url"] = f"/static/output/{user}/{media_type}/{pid_str}/storyboard/{filename}"

            cached_storyboard = json.dumps(panels)
            shared_memory.write("showrunner", "storyboard", cached_storyboard)
            with open(os.path.join(workspace_dir, "storyboard.json"), "w", encoding="utf-8") as f:
                f.write(cached_storyboard)
            
            shared_memory.write("showrunner", "approval_state", "pending")
            shared_memory.write("showrunner", "progress", "Storyboard: 100% (Awaiting Human Approval...)")
            return cached_storyboard

        shared_memory.write("showrunner", "progress", "Storyboard: 40% (Generating Panels...)")

        # 3. Call Model Router using 'storyboard' task type
        prompt = (
            "You are a professional storyboard artist. Generate visual panels for each scene in this script. "
            f"Script Details:\n{script_json}\n\n"
            "For each scene, design a detailed visual panel description detailing:\n"
            "- Aspect Ratio (e.g. 16:9)\n"
            "- Subject placement and composition (e.g. Rule of thirds, close-up, wide-angle)\n"
            "- Color Palette description (e.g. Deep emerald greens, cold cybernetic blues)\n"
            "- Specific visual elements in the frame\n"
            "Format your response as a JSON array of panels. Example format:\n"
            '[{"scene_number": 1, "aspect_ratio": "16:9", "composition": "Wide-angle", "colors": "Cold blues", "description": "Explorer in center looking at glowing light"}]\n'
            "Return ONLY raw JSON."
        )

        try:
            response = model_router.generate(prompt, "storyboard")
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()

            panels = json.loads(response_clean)
            for i, panel in enumerate(panels):
                scene_num = panel.get("scene_number", i + 1)
                comp = panel.get("composition", "Close-up")
                col = panel.get("colors", "Moody colors")
                desc = panel.get("description", "Preview panel")
                
                filename = f"scene{scene_num}.png"
                ws_path = os.path.join(storyboard_dir, filename)
                static_path = os.path.join(static_storyboard_dir, filename)
                
                generate_storyboard_image(scene_num, comp, col, desc, static_path)
                generate_storyboard_image(scene_num, comp, col, desc, ws_path)
                panel["image_url"] = f"/static/output/{user}/{media_type}/{pid_str}/storyboard/{filename}"

            response_clean = json.dumps(panels)
            shared_memory.write("showrunner", "storyboard", response_clean)
            shared_memory.write("cache", f"storyboard:{movie_goal}:{user}", response_clean)
            
            with open(os.path.join(workspace_dir, "storyboard.json"), "w", encoding="utf-8") as f:
                f.write(response_clean)
            
            shared_memory.write("showrunner", "approval_state", "pending")
            shared_memory.write("showrunner", "progress", "Storyboard: 100% (Awaiting Human Approval...)")
            return response_clean
        except Exception as e:
            self.logger.warning(f"Storyboard agent failed: {e}. Loading fallback panels.")
            fallback_list = [
                {
                    "scene_number": 1,
                    "aspect_ratio": "16:9",
                    "composition": "Establishing shot, camera sliding slowly down a mossy tree trunk. Rule of thirds.",
                    "colors": "Cold dark greens, mystical cyan glow in center.",
                    "description": "Lone explorer standing on forest floor path looking down at a bright blue crystal."
                },
                {
                    "scene_number": 2,
                    "aspect_ratio": "16:9",
                    "composition": "Low-angle medium shot looking up at the holographic city lines rising.",
                    "colors": "Vibrant glowing pinks, electric purple grid, cyberpunk aesthetic.",
                    "description": "Hologram glowing brightly in the forest, lighting up the explorer's shocked expression."
                },
                {
                    "scene_number": 3,
                    "aspect_ratio": "16:9",
                    "composition": "Over-the-shoulder tracking shot as the explorer steps forward.",
                    "colors": "Blinding warm golden portal light, transitioning to cybernetic neon.",
                    "description": "Explorer silhouette stepping into the shimmering gateway of solid blue-gold light."
                }
            ]
            for i, panel in enumerate(fallback_list):
                scene_num = panel.get("scene_number", i + 1)
                comp = panel.get("composition")
                col = panel.get("colors")
                desc = panel.get("description")
                
                filename = f"scene{scene_num}.png"
                ws_path = os.path.join(storyboard_dir, filename)
                static_path = os.path.join(static_storyboard_dir, filename)
                
                generate_storyboard_image(scene_num, comp, col, desc, static_path)
                generate_storyboard_image(scene_num, comp, col, desc, ws_path)
                panel["image_url"] = f"/static/output/{user}/{media_type}/{pid_str}/storyboard/{filename}"

            fallback = json.dumps(fallback_list)
            shared_memory.write("showrunner", "storyboard", fallback)
            with open(os.path.join(workspace_dir, "storyboard.json"), "w", encoding="utf-8") as f:
                f.write(fallback)
            
            shared_memory.write("showrunner", "approval_state", "pending")
            shared_memory.write("showrunner", "progress", "Storyboard: 100% (Awaiting Human Approval...)")
            return fallback
