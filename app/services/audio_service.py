"""Audio Service — clean wrapper for Qwen CosyVoice TTS voice synthesis.

Architecture:
    showrunner_audio plugin
          │
          ▼
    AudioService           ← this module
          │
          ▼
    QwenTTSClient  ──►  DashScope CosyVoice API
          │
          ▼
    audio.mp3 / audio_url

Usage:
    from app.services.audio_service import AudioService

    svc = AudioService()
    ok = svc.synthesize("Hello, this is AgentSphere OS.", output_path="voice.mp3")
"""

from __future__ import annotations

import os
from typing import Optional
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger("agentsphere.services.audio")

# Available CosyVoice voices (DashScope standard)
VOICES = {
    "female_en": "cherry",
    "male_en":   "canyon",
    "female_zh": "loongstella",
    "male_zh":   "longshu",
    "narrator":  "cherry",
    "default":   "cherry",
}


class AudioService:
    """High-level audio synthesis service wrapping QwenTTSClient."""

    def __init__(
        self,
        model: str = "cosyvoice-v1",
        voice: str = "cherry",
        api_key: Optional[str] = None,
    ) -> None:
        from app.llm.tts_client import QwenTTSClient

        self.model = model
        self.voice = voice
        self._client = QwenTTSClient(api_key=api_key)
        logger.info(f"[AudioService] Initialized with model={model}, voice={voice}")

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
    ) -> bool:
        """Synthesize text to speech and save to output_path.

        Args:
            text:        The narration/dialogue text to synthesize.
            output_path: Destination file path (e.g., ``audio/scene1.mp3``).
            voice:       CosyVoice voice ID override.
            model:       TTS model override.

        Returns:
            True if synthesis succeeded, False otherwise.
        """
        active_voice = voice or self.voice
        active_model = model or self.model

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        logger.info(
            f"[AudioService] Synthesizing {len(text)} chars "
            f"(model={active_model}, voice={active_voice}) → {output_path}"
        )
        success = self._client.synthesize(
            text=text,
            voice=active_voice,
            output_path=output_path,
            model=active_model,
        )
        if success:
            logger.info(f"[AudioService] Audio saved to {output_path}")
        else:
            logger.warning(f"[AudioService] Synthesis failed for: {text[:60]}...")
        return success

    def synthesize_scenes(
        self,
        scenes: list[dict],
        output_dir: str,
        voice: Optional[str] = None,
    ) -> list[str]:
        """Synthesize audio for a list of scene dicts and return file paths.

        Args:
            scenes:     List of scene dicts with ``narration``, ``dialogue``, or ``text`` fields.
            output_dir: Directory to write MP3 files.
            voice:      Voice override for all scenes.

        Returns:
            List of MP3 file paths (one per scene).
        """
        os.makedirs(output_dir, exist_ok=True)
        paths: list[str] = []

        for i, scene in enumerate(scenes):
            # Extract narration text from various scene formats
            if isinstance(scene, str):
                text = scene
            elif isinstance(scene, dict):
                # Try multiple field names in order of preference
                dialogues = scene.get("dialogues", [])
                if dialogues and isinstance(dialogues, list):
                    text = " ".join(d.get("text", "") for d in dialogues if isinstance(d, dict))
                else:
                    text = (
                        scene.get("narration")
                        or scene.get("dialogue")
                        or scene.get("text")
                        or scene.get("description", "")
                    )
            else:
                text = str(scene)

            text = text.strip()
            if not text:
                logger.warning(f"[AudioService] Scene {i+1} has no narration text, skipping.")
                continue

            output_path = os.path.join(output_dir, f"scene_{i+1:02d}_voice.mp3")
            success = self.synthesize(text, output_path=output_path, voice=voice)
            if success:
                paths.append(output_path)

        logger.info(f"[AudioService] Synthesized {len(paths)}/{len(scenes)} scenes.")
        return paths

    @property
    def active_model(self) -> str:
        """Return the currently configured TTS model name."""
        return self.model
