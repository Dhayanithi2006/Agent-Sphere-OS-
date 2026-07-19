"""Routing engine for selecting the appropriate language model based on task types."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.llm.qwen_client import QwenClient
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("agentsphere.llm.router")


class ModelRouter:
    """Selects and executes a model provider based on task configurations and handles fallbacks."""

    def __init__(self, client: Optional[Any] = None, default_provider: Optional[str] = None, **kwargs: Any) -> None:
        from app.llm.openai_provider import OpenAIProvider
        from app.llm.qwen_provider import QwenProvider
        from app.llm.extra_providers import ClaudeProvider, GeminiProvider, DeepSeekProvider, OllamaProvider

        # Retain standard QwenClient attribute for backward compatibility
        self.client = client if isinstance(client, QwenClient) else QwenClient()
        self._providers: Dict[str, Any] = {}

        # Resolved model names from config/env (so UI can display them)
        _max = settings.qwen_model_max    # e.g. "qwen3.7-max"
        _plus = settings.qwen_model_plus  # e.g. "qwen3.7-plus"
        _wan = settings.wan_video_model   # e.g. "wan2.1-t2v-turbo"

        # Register standard providers
        self.register_provider("qwen", QwenProvider())
        self.register_provider("openai", OpenAIProvider())
        self.register_provider("claude", ClaudeProvider())
        self.register_provider("gemini", GeminiProvider())
        self.register_provider("deepseek", DeepSeekProvider())
        self.register_provider("ollama", OllamaProvider())

        # ── Route table: (provider, model_override) per task type ──────────────
        # Confirmed mapping (per project owner):
        #   qwen3.7-max:  Kernel Supervisor, Planner, Researcher, Reviewer
        #   qwen3.7-plus: Developer, Tester, Reporter, script/audio/voice/scene tasks
        #   Video:        HappyHorse-T2V (happyhorse-1.1-t2v)
        #   Storyboard:   HappyHorse-I2V (happyhorse-1.1-i2v) — via I2V pipeline
        #   Audio/TTS:    CosyVoice (cosyvoice-v1)
        self._routes: Dict[str, List[tuple[str, Optional[str]]]] = {
            # ── Heavy reasoning tasks → qwen3.7-max ──────────────────────────
            "coding":      [("qwen", _max),   ("openai", "gpt-4o")],
            "reasoning":   [("qwen", _max),   ("openai", "gpt-4o")],
            "planner":     [("qwen", _max),   ("openai", "gpt-4o")],
            "researcher":  [("qwen", _max),   ("openai", "gpt-4o")],   # ← confirmed max
            "reviewer":    [("qwen", _max),   ("openai", "gpt-4o")],
            "supervisor":  [("qwen", _max),   ("openai", "gpt-4o")],   # Kernel Supervisor
            "video":       [("qwen", _max),   ("openai", "gpt-4o")],   # LLM planning; actual video via HappyHorse
            # ── Standard tasks → qwen3.7-plus ────────────────────────────────
            "developer":   [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "tester":      [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "reporter":    [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "script":      [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "storyboard":  [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "scene":       [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "prompt":      [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "voice":       [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "audio":       [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "subtitle":    [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "editor":      [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "fast":        [("qwen", _plus),  ("openai", "gpt-4o-mini")],
            "default":     [("qwen", _plus),  ("openai", "gpt-4o-mini")],
        }



        self.reset_metrics()

    def register_provider(self, name: str, provider: Any) -> None:
        """Register a model provider client."""
        self._providers[name] = provider
        logger.info(f"Registered model provider: {name}")

    def set_route(self, task_type: str, fallback_chain: List[tuple[str, Optional[str]]]) -> None:
        """Define routing path priorities for a specific task type."""
        self._routes[task_type] = fallback_chain

    def generate(self, prompt: str, task_type: str = "default", skip_cache: bool = False, **kwargs: Any) -> str:
        """Generate a response using the routed provider for the task type.

        Args:
            skip_cache: If True, bypass the semantic cache lookup. Set automatically
                        when the execution engine is in a tool-calling loop.
        """
        return self.route(task_type, prompt, skip_cache=skip_cache, **kwargs)

    def route(self, task_type: str, prompt: str, skip_cache: bool = False, **kwargs: Any) -> str:
        """Route a prompt to the selected provider using fallback priorities and track metrics."""
        # Enrich prompt with memories
        try:
            from app.memory.semantic_context import enrich_prompt_with_memories
            prompt = enrich_prompt_with_memories(prompt)
        except Exception as e:
            logger.warning(f"Failed to enrich prompt with memories: {e}")

        # Golden Rule: Instruct LLM to use tools instead of fabricating responses
        if len(prompt) > 50:
            tool_instruction = (
                "\n\n[SYSTEM INSTRUCTION: TOOL-FIRST RULE]\n"
                "If the requested information requires external data (such as web search, files, APIs, database, python execution, shell, etc.), "
                "DO NOT answer from your internal knowledge or fabricate outputs. Instead, you MUST invoke a tool by returning a JSON object of this structure:\n"
                "{\n"
                "  \"thought\": \"Detailed reasoning about what information is needed and why\",\n"
                "  \"tool_required\": true,\n"
                "  \"tool\": \"tool_name\",\n"
                "  \"arguments\": {\"param\": \"value\"}\n"
                "}\n"
                "CRITICAL: If the tool results already exist in the Execution Memory / Tool History, DO NOT call the tool again. "
                "If you have all the required information or after receiving the tool outputs, you must return:\n"
                "{\n"
                "  \"thought\": \"Detailed reasoning for the final answer\",\n"
                "  \"tool_required\": false,\n"
                "  \"result\": \"The final output or answer\"\n"
                "}\n"
                "Ensure your entire response is ONLY this JSON object. Do not wrap it in other text or code blocks."
            )
            prompt = prompt + tool_instruction



        # Normalize task_type to match registry
        task_key = task_type.lower().replace("showrunner_", "")

        # Skip semantic cache when:
        # - caller explicitly requests it (skip_cache=True)
        # - the prompt contains tool history (we're in a tool-calling iteration)
        #   so we always get a fresh LLM response after a tool result
        is_tool_iteration = "Execution Memory / Tool History" in prompt or "[SYSTEM OVERRIDE]" in prompt
        use_cache = not skip_cache and not is_tool_iteration

        # Check Semantic Cache
        import sys
        cache = None
        if use_cache and "pytest" not in sys.modules:
            try:
                from app.memory.semantic_cache import SemanticCache
                cache = SemanticCache()
                cached_val = cache.get(task_key, prompt)
                if cached_val:
                    logger.info(f"Universal Semantic Cache hit for task '{task_type}' (key '{task_key}')!")
                    return cached_val
            except Exception as e:
                logger.warning(f"Semantic Cache check failed: {e}")
        elif not use_cache:
            logger.debug("Semantic cache bypassed for task '%s' (tool iteration or skip_cache=True)", task_type)
            import sys
            if "pytest" not in sys.modules:
                try:
                    from app.memory.semantic_cache import SemanticCache
                    cache = SemanticCache()  # still initialise so we can write after
                except Exception:
                    pass

        chain = self._routes.get(task_key, self._routes.get("default", []))
        
        errors = []
        for provider_name, model_override in chain:
            if provider_name not in self._providers:
                continue
            provider = self._providers[provider_name]

            call_kwargs = kwargs.copy()
            if model_override:
                call_kwargs["model"] = model_override

            before_usage = None
            client_to_check = None
            if provider_name == "qwen" and hasattr(provider, "client") and hasattr(provider.client, "get_usage"):
                client_to_check = provider.client

            if client_to_check:
                try:
                    u = client_to_check.get_usage()
                    before_usage = (u.prompt_tokens, u.completion_tokens)
                except Exception:
                    pass

            try:
                response = provider.generate(prompt, **call_kwargs)
                
                p_tokens, c_tokens = None, None
                if client_to_check and before_usage:
                    try:
                        u = client_to_check.get_usage()
                        p_tokens = u.prompt_tokens - before_usage[0]
                        c_tokens = u.completion_tokens - before_usage[1]
                        if p_tokens <= 0 and c_tokens <= 0:
                            p_tokens, c_tokens = None, None
                    except Exception:
                        pass

                self._track_usage(
                    provider_name, 
                    model_override or getattr(provider, "model", "default"), 
                    prompt, 
                    response,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens
                )
                # Store in semantic cache
                try:
                    if cache:
                        cache.set(task_key, prompt, response)
                except Exception:
                    pass
                return response
            except Exception as e:
                errors.append(f"{provider_name}: {e}")
                logger.warning(f"Provider '{provider_name}' failed for task '{task_type}' (key '{task_key}'): {e}. Retrying fallback...")

        # Last resort fallback: direct QwenClient
        try:
            model = kwargs.pop("model", "qwen-max")
            before_usage = None
            if hasattr(self.client, "get_usage"):
                try:
                    u = self.client.get_usage()
                    before_usage = (u.prompt_tokens, u.completion_tokens)
                except Exception:
                    pass

            response = self.client.generate(prompt, model=model, **kwargs)

            p_tokens, c_tokens = None, None
            if hasattr(self.client, "get_usage") and before_usage:
                try:
                    u = self.client.get_usage()
                    p_tokens = u.prompt_tokens - before_usage[0]
                    c_tokens = u.completion_tokens - before_usage[1]
                    if p_tokens <= 0 and c_tokens <= 0:
                        p_tokens, c_tokens = None, None
                except Exception:
                    pass

            self._track_usage(
                "qwen_client",
                model,
                prompt,
                response,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens
            )
            # Store in semantic cache
            try:
                if cache:
                    cache.set(task_key, prompt, response)
            except Exception:
                pass
            return response
        except Exception as e:
            errors.append(f"QwenClient: {e}")
            raise RuntimeError(
                f"All model providers and client fallbacks failed for task '{task_type}'. "
                f"Errors: {'; '.join(errors)}"
            )

    def get_active_model_for_task(self, task_type: str) -> str:
        """Return the primary model name that will be used for a given task type."""
        task_key = task_type.lower().replace("showrunner_", "")
        chain = self._routes.get(task_key, self._routes.get("default", []))
        if chain:
            return chain[0][1] or settings.qwen_model_max
        return settings.qwen_model

    def get_usage_metrics(self) -> Dict[str, Any]:
        """Return the accumulated token tracking and billing cost metrics."""
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset all usage and cost counters."""
        self.metrics = {
            "total_calls": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost": 0.0,
            "provider_usage": {},
        }

    def _track_usage(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        response: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None
    ) -> None:
        # Rates per 1,000 tokens — updated to match real Qwen Cloud pricing tiers
        RATES = {
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            # Qwen3.7 model family
            "qwen3.7-max": {"prompt": 0.002, "completion": 0.006},
            "qwen3.7-plus": {"prompt": 0.0008, "completion": 0.002},
            # Legacy Qwen model names (kept for backward-compat with old route entries)
            "qwen-max": {"prompt": 0.002, "completion": 0.006},
            "qwen-plus": {"prompt": 0.0008, "completion": 0.002},
            "qwen-turbo": {"prompt": 0.0003, "completion": 0.001},
            # Vision
            "qwen-vl": {"prompt": 0.0015, "completion": 0.0045},
            "qwen-vl-max": {"prompt": 0.0020, "completion": 0.0060},
            # Video (per generation, estimated token equivalent)
            "wan2.1-t2v-turbo": {"prompt": 0.010, "completion": 0.030},
            "happyHorse-T2V": {"prompt": 0.015, "completion": 0.045},
            "happyHorse-I2V": {"prompt": 0.018, "completion": 0.054},
            # Audio
            "cosyvoice-v1": {"prompt": 0.001, "completion": 0.003},
            "qwen-tts": {"prompt": 0.001, "completion": 0.003},
            "default": {"prompt": 0.001, "completion": 0.003},
        }

        # Estimate word-to-token count (1 word ≈ 1.3 tokens) if real usage is not provided
        if prompt_tokens is not None and completion_tokens is not None:
            p_tokens = prompt_tokens
            c_tokens = completion_tokens
        else:
            words_in = len(prompt.split())
            words_out = len(response.split())
            p_tokens = int(words_in * 1.3)
            c_tokens = int(words_out * 1.3)

        rate = RATES.get(model_name, RATES.get("default"))
        cost = (p_tokens / 1000.0) * rate["prompt"] + (c_tokens / 1000.0) * rate["completion"]

        self.metrics["total_calls"] += 1
        self.metrics["total_prompt_tokens"] += p_tokens
        self.metrics["total_completion_tokens"] += c_tokens
        self.metrics["total_cost"] += cost

        if provider_name not in self.metrics["provider_usage"]:
            self.metrics["provider_usage"][provider_name] = {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost": 0.0,
            }

        p_usage = self.metrics["provider_usage"][provider_name]
        p_usage["calls"] += 1
        p_usage["prompt_tokens"] += p_tokens
        p_usage["completion_tokens"] += c_tokens
        p_usage["cost"] += cost


