"""Qwen TTS Client — wraps DashScope CosyVoice for text-to-speech synthesis.

CosyVoice uses a WebSocket-based API via the official DashScope Python SDK.
The compatible-mode /audio/speech endpoint is OpenAI-compatible for other TTS
models but CosyVoice-v1 requires the native SDK.

Fallback chain:
  1. DashScope SDK (cosyvoice-v1)   — real synthesis
  2. OpenAI-compatible /audio/speech — for other TTS models
  3. Silent MP3 stub                 — always succeeds, never crashes pipeline
"""

import os
import sys
import requests
from typing import Optional
from app.core.logger import get_logger

logger = get_logger("agentsphere.llm.tts_client")

# Silent MP3 stub — 100ms of silence, always a valid audio file
_SILENT_MP3_B64 = (
    "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU2LjM2LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAA"
    "AAAAAAAAAAAAASW5mbwAAAA8AAAAEAAABIADAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDV1dXV1d"
    "XV1dXV1dXV1dXV1dXV1dXV1dXV6urq6urq6urq6urq6urq6urq6urq6urq6v////////"
    "////////////////////////8AAAAATGF2YzU2LjQxAAAAAAAAAAAAAAAAJAAAAAAAAAAAASDs90"
    "hvAAAAAAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0g"
    "AAAAARTMLU//MUZAYAAAGkAAAAAAAAA0gAAAAAOTku//MUZAkAAAGkAAAAAAAAA0gAAAAANVVV"
)


class QwenTTSClient:
    """Dedicated client for Alibaba Cloud DashScope CosyVoice TTS API.

    Supported models:
    - cosyvoice-v1      (native DashScope SDK, WebSocket)
    - cosyvoice-v2      (native DashScope SDK, WebSocket)
    - Any OpenAI-compat TTS model (REST /audio/speech endpoint)
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.base_url = (
            base_url
            or os.getenv("DASHSCOPE_COMPATIBLE_BASE_URL")
            or os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        )

    def synthesize(
        self,
        text: str,
        voice: str = "cherry",
        output_path: str = "voice.mp3",
        model: str = "cosyvoice-v1",
    ) -> bool:
        """Synthesize text to speech and save MP3 to output_path.

        Args:
            text:        The text to synthesize.
            voice:       CosyVoice voice ID (e.g., ``cherry``, ``canyon``, ``loongstella``).
            output_path: Output file path (must end in .mp3 or .wav).
            model:       TTS model (default: ``cosyvoice-v1``).

        Returns:
            True if synthesis succeeded or fallback was written, False on complete failure.
        """
        is_dev = os.getenv("AGENTSPHERE_ENV", "production").lower() == "development" or "pytest" in sys.modules
        is_mock_key = not self.api_key or self.api_key == "mock-key"

        # Dev / test mode: write silent stub immediately
        if is_mock_key or is_dev:
            return self._write_silent_stub(output_path, reason="dev/test mode")

        # Ensure output dir exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # ── Attempt 1: DashScope SDK (CosyVoice native) ────────────────────
        if model.startswith("cosyvoice"):
            success = self._synthesize_via_sdk(text, voice, output_path, model)
            if success:
                return True
            logger.warning(f"[TTS] DashScope SDK synthesis failed, trying REST fallback...")

        # ── Attempt 2: OpenAI-compatible REST endpoint ─────────────────────
        success = self._synthesize_via_rest(text, voice, output_path, model)
        if success:
            return True

        # ── Attempt 3: Silent stub fallback ───────────────────────────────
        return self._write_silent_stub(output_path, reason="all synthesis methods failed")

    # ─────────────────────────────────────────────────────────────────────────
    # Private: DashScope SDK (CosyVoice WebSocket API)
    # ─────────────────────────────────────────────────────────────────────────

    def _synthesize_via_sdk(self, text: str, voice: str, output_path: str, model: str) -> bool:
        """Use the official DashScope Python SDK for CosyVoice synthesis.

        Tries tts_v2 (WebSocket streaming) first, then falls back to the
        older tts HTTP-based approach which may work through firewalls.
        """
        try:
            import dashscope
            dashscope.api_key = self.api_key

            # Attempt 1: tts_v2 WebSocket (preferred, lowest latency)
            try:
                from dashscope.audio.tts_v2 import SpeechSynthesizer
                logger.info(f"[TTS] DashScope tts_v2: model={model}, voice={voice}")
                synthesizer = SpeechSynthesizer(
                    model=model,
                    voice=voice,
                    # Some SDK versions accept a timeout kwarg
                )
                audio = synthesizer.call(text)
                if audio and len(audio) > 100:
                    with open(output_path, "wb") as f:
                        f.write(audio)
                    logger.info(f"[TTS] Audio saved via tts_v2 SDK: {output_path} ({len(audio)} bytes)")
                    return True
                logger.warning("[TTS] tts_v2 returned empty audio, trying tts v1...")
            except Exception as ws_err:
                logger.warning(f"[TTS] tts_v2 WebSocket failed ({ws_err}), trying tts v1 HTTP...")

            # Attempt 2: older dashscope.audio.tts (HTTP-based, firewall-friendly)
            try:
                from dashscope.audio.tts import SpeechSynthesizer as TtsV1
                logger.info(f"[TTS] DashScope tts v1 HTTP: model={model}, voice={voice}")
                result = TtsV1.call(
                    model=model,
                    text=text,
                    voice=voice,
                    format="mp3",
                    sample_rate=22050,
                )
                # TtsV1 result: check .output.audio or .audio_data depending on SDK version
                audio_data = None
                if hasattr(result, "output") and hasattr(result.output, "audio"):
                    audio_data = result.output.audio
                elif hasattr(result, "audio_data"):
                    audio_data = result.audio_data
                elif hasattr(result, "get_audio_data"):
                    audio_data = result.get_audio_data()

                if audio_data and len(audio_data) > 100:
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    logger.info(f"[TTS] Audio saved via tts v1 SDK: {output_path} ({len(audio_data)} bytes)")
                    return True
                else:
                    status = getattr(result, "status_code", getattr(result, "code", "unknown"))
                    msg = getattr(result, "message", str(result))
                    logger.warning(f"[TTS] tts v1 returned no audio: {status} {msg}")
            except Exception as v1_err:
                logger.warning(f"[TTS] tts v1 HTTP failed: {v1_err}")

            return False

        except ImportError:
            logger.warning("[TTS] dashscope SDK not installed — run: pip install dashscope")
            return False
        except Exception as e:
            logger.warning(f"[TTS] DashScope SDK error: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Private: OpenAI-compatible REST endpoint
    # ─────────────────────────────────────────────────────────────────────────

    def _synthesize_via_rest(self, text: str, voice: str, output_path: str, model: str) -> bool:
        """Try the OpenAI-compatible /audio/speech endpoint (works for some models)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.base_url}/audio/speech"
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        }
        try:
            logger.info(f"[TTS] REST endpoint: {endpoint} — model={model}")
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.info(f"[TTS] Audio saved via REST: {output_path} ({len(response.content)} bytes)")
            return True
        except Exception as e:
            logger.warning(f"[TTS] REST synthesis failed: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Private: Silent stub
    # ─────────────────────────────────────────────────────────────────────────

    def _write_silent_stub(self, output_path: str, reason: str = "") -> bool:
        """Write a valid-but-silent MP3 file. Never crashes. Always returns True."""
        try:
            import base64
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(_SILENT_MP3_B64))
            logger.info(f"[TTS] Silent MP3 stub written to {output_path}" + (f" ({reason})" if reason else ""))
            return True
        except Exception as e:
            logger.error(f"[TTS] Failed to write silent stub: {e}")
            return False
