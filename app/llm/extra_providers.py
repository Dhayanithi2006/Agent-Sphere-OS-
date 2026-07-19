"""Additional model providers for Claude, Gemini, DeepSeek, and Ollama endpoints."""

from __future__ import annotations

import os
import urllib.request
import urllib.parse
import json
from typing import Any
from app.llm.provider_base import BaseModelProvider
from app.core.logging import get_logger

logger = get_logger("agentsphere.llm.extra_providers")


class ClaudeProvider(BaseModelProvider):
    """Anthropic Claude LLM Provider."""

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(name="claude")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self.api_key:
            logger.warning("Anthropic API key is not configured. Falling back to a stub.")
            return f"[claude stub] {prompt}"

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body["content"][0]["text"]
        except Exception as e:
            logger.error(f"Claude API failed: {e}")
            return f"Claude generation failed: {e}"


class GeminiProvider(BaseModelProvider):
    """Google Gemini LLM Provider."""

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(name="gemini")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self.api_key:
            logger.warning("Gemini API key is not configured. Falling back to a stub.")
            return f"[gemini stub] {prompt}"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini API failed: {e}")
            return f"Gemini generation failed: {e}"


class DeepSeekProvider(BaseModelProvider):
    """DeepSeek LLM Provider."""

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(name="deepseek")
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self.api_key:
            logger.warning("DeepSeek API key is not configured. Falling back to a stub.")
            return f"[deepseek stub] {prompt}"

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API failed: {e}")
            return f"DeepSeek generation failed: {e}"


class OllamaProvider(BaseModelProvider):
    """Local Ollama LLM Provider."""

    def __init__(self, host: str | None = None) -> None:
        super().__init__(name="ollama")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        url = f"{self.host}/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body["response"]
        except Exception as e:
            logger.warning(f"Ollama connection failed: {e}. Falling back to a stub.")
            return f"[ollama stub] {prompt}"
