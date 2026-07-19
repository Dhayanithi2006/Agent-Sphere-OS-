"""Image Service — Qwen image generation API with SVG fallback poster.

Architecture:
    showrunner_poster plugin
          │
          ▼
    ImageService           ← this module
          │
          ├── [Real API] DashScope Image Generation (wanx-v1 / flux)
          └── [Fallback]  Qwen LLM → Generates rich SVG poster

Usage:
    from app.services.image_service import ImageService

    svc = ImageService()
    poster_path = svc.generate_poster(
        movie_goal="An AI awakening on Mars",
        output_path="posters/poster.png",
    )
"""

from __future__ import annotations

import os
import json
import base64
import requests
from typing import Optional
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger("agentsphere.services.image")


class ImageService:
    """Image generation service for posters, thumbnails, and storyboard frames.

    Falls back gracefully:
    1. Qwen Image Generation API (wanx-v1 or configured model)
    2. Rich SVG poster generated from Qwen LLM description
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model or settings.qwen_image_model
        self.api_key = api_key or settings.qwen_api_key
        # DashScope image generation endpoint
        base = settings.qwen_base_url.replace("/compatible-mode/v1", "/api/v1")
        self.image_endpoint = f"{base}/services/aigc/text2image/image-synthesis"
        logger.info(f"[ImageService] Initialized with model={self.model}")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def generate_poster(
        self,
        movie_goal: str,
        output_path: str,
        style: str = "cinematic",
        genre: str = "",
    ) -> str:
        """Generate a movie poster image.

        Attempts the DashScope image API first; falls back to a rich SVG poster.

        Args:
            movie_goal:  The movie concept / title.
            output_path: Where to save the poster (PNG or SVG).
            style:       Visual style hint (e.g., "cinematic", "animated", "noir").
            genre:       Genre hint (e.g., "Sci-Fi", "Horror").

        Returns:
            Local file path of the saved poster.
        """
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        # Try real image API
        if self.api_key and self.api_key != "mock-key":
            img_path = self._try_image_api(movie_goal, output_path, style, genre)
            if img_path:
                return img_path

        # Fallback: rich SVG poster via LLM
        logger.info("[ImageService] Falling back to SVG poster generation via LLM")
        # Use .svg extension for the fallback poster
        if output_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            svg_path = output_path.rsplit(".", 1)[0] + ".svg"
        elif output_path.lower().endswith(".svg"):
            svg_path = output_path
        else:
            svg_path = output_path + ".svg"
        return self._generate_svg_poster(movie_goal, svg_path, style, genre)

    def generate_thumbnail(self, movie_goal: str, output_path: str) -> str:
        """Generate a thumbnail (16:9 ratio, smaller than poster)."""
        return self.generate_poster(movie_goal, output_path, style="thumbnail")

    # ─────────────────────────────────────────────────────────────────────────
    # Private: Real Image API
    # ─────────────────────────────────────────────────────────────────────────

    def _try_image_api(
        self,
        prompt_text: str,
        output_path: str,
        style: str,
        genre: str,
    ) -> Optional[str]:
        """Attempt DashScope image generation. Returns path or None on failure."""
        import sys
        is_dev = os.getenv("AGENTSPHERE_ENV", "production").lower() == "development" or "pytest" in sys.modules
        if is_dev:
            return None  # Skip real API in dev/test

        full_prompt = (
            f"A stunning {style} movie poster for: '{prompt_text}'. "
            f"Genre: {genre or 'Drama'}. "
            "Cinematic lighting, dramatic composition, high quality, 4K."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": self.model,
            "input": {"prompt": full_prompt},
            "parameters": {
                "size": "768*1024",
                "n": 1,
                "style": "<cinematic>",
            },
        }

        try:
            logger.info(f"[ImageService] Calling image API: {self.model}")
            resp = requests.post(self.image_endpoint, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Handle async task
            task_id = data.get("output", {}).get("task_id")
            if task_id:
                return self._poll_image_task(task_id, output_path)

            # Handle synchronous response (some models)
            results = data.get("output", {}).get("results", [])
            if results:
                img_url = results[0].get("url")
                if img_url:
                    return self._download_image(img_url, output_path)

        except Exception as e:
            logger.warning(f"[ImageService] Image API call failed: {e}")

        return None

    def _poll_image_task(self, task_id: str, output_path: str, max_wait: float = 120.0) -> Optional[str]:
        """Poll a DashScope image generation async task."""
        import time
        base = settings.qwen_base_url.replace("/compatible-mode/v1", "/api/v1")
        task_url = f"{base}/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        start = time.time()
        while time.time() - start < max_wait:
            try:
                resp = requests.get(task_url, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                output = data.get("output", {})
                status = output.get("task_status", "PENDING").upper()

                if status == "SUCCEEDED":
                    results = output.get("results", [])
                    if results:
                        img_url = results[0].get("url")
                        if img_url:
                            return self._download_image(img_url, output_path)

                if status == "FAILED":
                    logger.error(f"[ImageService] Image task {task_id} failed")
                    return None

            except Exception as e:
                logger.warning(f"[ImageService] Polling error: {e}")

            time.sleep(3.0)

        logger.warning(f"[ImageService] Image task {task_id} timed out")
        return None

    def _download_image(self, url: str, output_path: str) -> Optional[str]:
        """Download an image from URL and save to output_path."""
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"[ImageService] Image downloaded to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"[ImageService] Download failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Private: SVG Poster Fallback
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_svg_poster(
        self,
        movie_goal: str,
        output_path: str,
        style: str,
        genre: str,
    ) -> str:
        """Use the Qwen LLM to create a rich, detailed SVG movie poster.

        The LLM generates visual composition parameters; we render them as SVG.
        """
        try:
            from app.llm.qwen_client import QwenClient
            client = QwenClient(model=settings.qwen_model_plus)

            prompt = (
                f"You are a professional movie poster designer. For the movie concept: '{movie_goal}' "
                f"(genre: {genre or 'Drama'}, style: {style}), "
                "return ONLY a JSON object with these fields:\n"
                "- title: the movie title (max 5 words)\n"
                "- tagline: a compelling one-liner tagline\n"
                "- primary_color: a hex color for the dominant palette (e.g. '#1A0A3D')\n"
                "- accent_color: a hex accent color\n"
                "- mood: one word describing the visual mood\n"
                "- visual_elements: array of 3 key visual elements to depict\n"
                "Return only the JSON, no markdown."
            )

            logger.info("[ImageService] Asking LLM for poster visual parameters...")
            raw = client.generate(prompt, model=settings.qwen_model_plus, temperature=0.7)
            design = json.loads(raw) if isinstance(raw, str) else {}
        except Exception as e:
            logger.warning(f"[ImageService] LLM poster design failed ({e}), using defaults")
            design = {}

        # Render SVG poster
        title = design.get("title", movie_goal[:40])
        tagline = design.get("tagline", "The story of a lifetime.")
        primary = design.get("primary_color", "#0D0D2B")
        accent = design.get("accent_color", "#FFB800")
        mood = design.get("mood", "Epic")
        elements = design.get("visual_elements", ["stars", "shadows", "light"])
        genre_label = (genre or "Drama").upper()

        svg = self._render_poster_svg(title, tagline, primary, accent, mood, elements, genre_label, style)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg)

        logger.info(f"[ImageService] SVG poster saved to {output_path}")
        return output_path

    def _render_poster_svg(
        self,
        title: str,
        tagline: str,
        primary: str,
        accent: str,
        mood: str,
        elements: list[str],
        genre: str,
        style: str,
    ) -> str:
        """Render a rich SVG movie poster."""
        # Escape XML
        def esc(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        el1 = esc(elements[0] if len(elements) > 0 else "")
        el2 = esc(elements[1] if len(elements) > 1 else "")
        el3 = esc(elements[2] if len(elements) > 2 else "")
        t = esc(title)
        tl = esc(tagline)
        m = esc(mood)
        g = esc(genre)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="768" height="1024" viewBox="0 0 768 1024" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{primary}"/>
      <stop offset="60%" stop-color="{self._darken(primary)}"/>
      <stop offset="100%" stop-color="#000000"/>
    </linearGradient>
    <linearGradient id="accentGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{accent}"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="textShadow">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.8"/>
    </filter>
    <radialGradient id="spotlight" cx="50%" cy="35%" r="55%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="{primary}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Background -->
  <rect width="768" height="1024" fill="url(#bgGrad)"/>
  <rect width="768" height="1024" fill="url(#spotlight)"/>

  <!-- Decorative stars / particles -->
  {''.join(f'<circle cx="{hash(el1+str(i*7))%750+9}" cy="{hash(el2+str(i*11))%400+50}" r="{1 + (i%3)}" fill="{accent}" opacity="{0.3 + (i%5)*0.12:.1f}"/>' for i in range(30))}

  <!-- Central visual element placeholder -->
  <ellipse cx="384" cy="400" rx="280" ry="320" fill="{primary}" opacity="0.3" filter="url(#glow)"/>
  <ellipse cx="384" cy="380" rx="200" ry="220" fill="{accent}" opacity="0.05"/>

  <!-- Visual element labels (artistic) -->
  <text x="384" y="300" font-family="Georgia, serif" font-size="13" fill="{accent}" opacity="0.4"
        text-anchor="middle" letter-spacing="6">{el1.upper()}</text>
  <text x="384" y="390" font-family="Georgia, serif" font-size="11" fill="white" opacity="0.25"
        text-anchor="middle" letter-spacing="4">{el2.upper()}</text>
  <text x="384" y="470" font-family="Georgia, serif" font-size="10" fill="{accent}" opacity="0.3"
        text-anchor="middle" letter-spacing="5">{el3.upper()}</text>

  <!-- Mood watermark -->
  <text x="384" y="550" font-family="Georgia, serif" font-size="72" fill="{primary}" opacity="0.06"
        text-anchor="middle" font-weight="bold">{m.upper()}</text>

  <!-- Accent bar -->
  <rect x="0" y="680" width="768" height="2" fill="url(#accentGrad)" opacity="0.7"/>
  <rect x="0" y="900" width="768" height="1" fill="url(#accentGrad)" opacity="0.4"/>

  <!-- Genre badge -->
  <rect x="50" y="720" width="120" height="28" rx="4" fill="none"
        stroke="{accent}" stroke-width="1" opacity="0.7"/>
  <text x="110" y="739" font-family="Arial, sans-serif" font-size="11" fill="{accent}"
        text-anchor="middle" letter-spacing="3" font-weight="600">{g}</text>

  <!-- TITLE -->
  <text x="384" y="810" font-family="Georgia, serif" font-size="52" fill="white"
        text-anchor="middle" font-weight="bold" filter="url(#textShadow)">{t}</text>

  <!-- Accent underline for title -->
  <rect x="184" y="820" width="400" height="2" rx="1" fill="{accent}" opacity="0.8"/>

  <!-- Tagline -->
  <text x="384" y="860" font-family="Georgia, serif" font-size="16" fill="{accent}"
        text-anchor="middle" font-style="italic" opacity="0.9">{tl}</text>

  <!-- Production footer -->
  <rect x="0" y="960" width="768" height="64" fill="#000000" opacity="0.5"/>
  <text x="384" y="988" font-family="Arial, sans-serif" font-size="9" fill="white"
        text-anchor="middle" opacity="0.5" letter-spacing="2">AGENTSPHERE STUDIOS PRESENTS</text>
  <text x="384" y="1008" font-family="Arial, sans-serif" font-size="8" fill="{accent}"
        text-anchor="middle" opacity="0.4" letter-spacing="4">POWERED BY QWEN CLOUD · AI PRODUCTION</text>
</svg>"""

    def _darken(self, hex_color: str) -> str:
        """Return a darker variant of a hex color."""
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r, g, b = max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#000000"
