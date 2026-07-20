"""Semantic Context Engine: Recalls and injects relevant memories into LLM prompt queries."""

from __future__ import annotations

from app.memory.memory_agent import MemoryAgent

memory_agent = MemoryAgent()

# Keywords that indicate the prompt is about user media/style preferences.
# Exported at module level so tests can assert the keyword list directly.
keywords = ["anime", "marvel", "superhero", "style", "voice", "duration", "genre", "tone"]


def enrich_prompt_with_memories(prompt: str) -> str:
    """Retrieve semantically relevant memories and inject them into the LLM system prompt context."""
    # Check if this prompt relates to preferences/genres we track
    if not any(kw in prompt.lower() for kw in keywords):
        return prompt

    memories = memory_agent.recall_memories(prompt, limit=2)
    if not memories:
        return prompt

    context_blocks = []
    for m in memories:
        context_blocks.append(f"- User Preset: {m['content']} (Source: {m['tier'].upper()} memory)")

    context_str = "\n".join(context_blocks)
    enriched_prompt = (
        "Instructions: Respect the following recalled user memory profile:\n"
        f"{context_str}\n\n"
        f"Prompt: {prompt}"
    )
    return enriched_prompt
