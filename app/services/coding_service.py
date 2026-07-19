"""Coding Service — clean wrapper for Qwen3.7-Max code generation.

Usage:
    from app.services.coding_service import generate_code, generate_code_with_review

    code = generate_code("Write a FastAPI endpoint that returns system metrics")
"""

from __future__ import annotations

import os
from typing import Optional
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger("agentsphere.services.coding")


def generate_code(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> str:
    """Generate code using Qwen3.7-Max via the QwenClient.

    Args:
        prompt:      The coding task description or specification.
        model:       Model override (defaults to qwen3.7-max from config).
        temperature: Lower = more deterministic code (default 0.3).
        max_tokens:  Optional token limit on the response.

    Returns:
        Generated code as a string.
    """
    from app.llm.qwen_client import QwenClient

    model = model or settings.qwen_model_max
    client = QwenClient(model=model)

    system_prompt = (
        "You are an expert software engineer. Write clean, well-documented, production-ready code. "
        "Always include docstrings and type hints. Do not add unnecessary explanations — return only the code."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    logger.info(f"[CodingService] Generating code with {model}")
    result = client.generate(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    logger.info(f"[CodingService] Generation complete ({len(str(result))} chars)")
    return result if isinstance(result, str) else "".join(list(result))


def generate_code_with_review(
    prompt: str,
    dev_model: Optional[str] = None,
    review_model: Optional[str] = None,
) -> dict[str, str]:
    """Generate code then run a self-review pass.

    Args:
        prompt:       The coding requirement.
        dev_model:    Model for generation (default: qwen3.7-max).
        review_model: Model for review pass (default: qwen3.7-max).

    Returns:
        dict with keys: ``code`` (original), ``review`` (review notes), ``final`` (reviewed code).
    """
    from app.llm.qwen_client import QwenClient

    dev_model = dev_model or settings.qwen_model_max
    review_model = review_model or settings.qwen_model_max
    client = QwenClient(model=dev_model)

    # Step 1 — Generate
    logger.info(f"[CodingService] Step 1: Generating code with {dev_model}")
    code = generate_code(prompt, model=dev_model)

    # Step 2 — Review
    review_prompt = (
        f"Review the following code for correctness, edge cases, and best practices. "
        f"Return the improved version with inline comments for any fixes.\n\n```\n{code}\n```"
    )
    review_messages = [
        {"role": "system", "content": "You are a senior code reviewer. Be concise and precise."},
        {"role": "user", "content": review_prompt},
    ]
    logger.info(f"[CodingService] Step 2: Code review with {review_model}")
    reviewed_client = QwenClient(model=review_model)
    review_result = reviewed_client.generate(review_messages, model=review_model, temperature=0.2)
    final = review_result if isinstance(review_result, str) else "".join(list(review_result))

    return {"code": code, "review": final, "final": final}
