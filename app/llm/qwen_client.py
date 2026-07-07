"""Thin client wrapper for Qwen-compatible LLM APIs (OpenAI-compatible)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Generator, Optional

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger("agentsphere.llm.qwen")


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QwenClient:
    """OpenAI-compatible client for Qwen Cloud APIs with streaming, retries, and token tracking."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = base_url or settings.qwen_base_url
        self.api_key = api_key or settings.qwen_api_key
        self.model = model or settings.qwen_model
        self.max_retries = max_retries or settings.qwen_max_retries
        self.timeout = timeout or settings.qwen_timeout

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        self.async_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        self.total_usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

    def _retry(self, func: callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic."""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        raise last_exception

    def generate(
        self,
        prompt: str | list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | Generator[str, None, None]:
        """Generate a response using the configured LLM endpoint."""
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        if stream:
            return self._generate_stream(messages, model or self.model, temperature, max_tokens, **kwargs)
        else:
            return self._generate_sync(messages, model or self.model, temperature, max_tokens, **kwargs)

    def _generate_sync(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
        **kwargs: Any,
    ) -> str:
        """Synchronous generation with token usage tracking."""
        def _call():
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        completion: ChatCompletion = self._retry(_call)

        if completion.usage:
            self.total_usage.prompt_tokens += completion.usage.prompt_tokens
            self.total_usage.completion_tokens += completion.usage.completion_tokens
            self.total_usage.total_tokens += completion.usage.total_tokens

        return completion.choices[0].message.content or ""

    def _generate_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """Streaming generation."""
        def _call():
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

        stream: Generator[ChatCompletionChunk, None, None] = self._retry(_call)

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def agenerate(
        self,
        prompt: str | list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | AsyncGenerator[str, None]:
        """Asynchronous generation."""
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        if stream:
            return self._agenerate_stream(messages, model or self.model, temperature, max_tokens, **kwargs)
        else:
            return await self._agenerate_sync(messages, model or self.model, temperature, max_tokens, **kwargs)

    async def _agenerate_sync(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
        **kwargs: Any,
    ) -> str:
        """Async sync generation with token usage tracking."""
        async def _call():
            return await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        completion: ChatCompletion = await self._retry(_call)

        if completion.usage:
            self.total_usage.prompt_tokens += completion.usage.prompt_tokens
            self.total_usage.completion_tokens += completion.usage.completion_tokens
            self.total_usage.total_tokens += completion.usage.total_tokens

        return completion.choices[0].message.content or ""

    async def _agenerate_stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int | None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Async streaming generation."""
        async def _call():
            return await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

        stream: AsyncGenerator[ChatCompletionChunk, None] = await self._retry(_call)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_usage(self) -> TokenUsage:
        """Return the total token usage."""
        return self.total_usage

    def reset_usage(self) -> None:
        """Reset the token usage counter."""
        self.total_usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
