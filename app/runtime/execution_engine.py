"""Execution engine responsible for running managed agents with resource and log tracking."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.agents.base_agent import BaseAgent
from app.core.logger import get_logger

try:
    import psutil
except ImportError:
    psutil = None


@dataclass(slots=True)
class ExecutionResult:
    """Outcome of an agent execution attempt, capturing outputs, logs, and resource usage metrics."""

    success: bool
    output: Any = None
    error: str | None = None
    agent_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    memory_used_mb: float = 0.0


class ExecutionEngine:
    """Executes agents, tracks logs, limits thread pool sizes, and monitors resource footprints."""

    def __init__(self) -> None:
        self.logger = get_logger("agentsphere.execution_engine")
        self._queue: deque[tuple[BaseAgent, dict[str, Any] | None]] = deque()
        self._history: list[dict[str, Any]] = []
        self._metrics: dict[str, int] = {"total_executions": 0, "success_count": 0, "failure_count": 0}
        self._processes: dict[str, dict[str, Any]] = {}
        self._max_workers: int | None = None

    def set_concurrency_limit(self, limit: int) -> None:
        """Dynamically configure the execution thread pool worker size limit."""
        if limit < 1:
            raise ValueError("Concurrency limit must be at least 1.")
        self._max_workers = limit
        self.logger.info("Configured parallel execution concurrency limit: %d workers", limit)

    def execute_agent(self, agent: BaseAgent, payload: dict[str, Any] | None = None) -> ExecutionResult:
        """Run an agent capturing logs, duration, and memory utilization metrics."""
        self.logger.info("Executing agent %s", agent.agent_id)

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        start_time = time.perf_counter()

        # Track process memory usage before run
        mem_before = 0.0
        if psutil is not None:
            try:
                mem_before = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        success = False
        output = None
        error = None

        # Redirect IO logs
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            try:
                if payload is None:
                    payload = {}

                attempt = 0
                max_attempts = 10
                previous_tool_call = None
                
                while attempt < max_attempts:
                    self.logger.debug("[EXEC] Attempt %d/%d for agent '%s'", attempt + 1, max_attempts, agent.agent_id)
                    step_output = agent.execute(payload)

                    # Guard against non-string outputs (e.g. AgentString subclass on some platforms)
                    if not isinstance(step_output, str):
                        step_output = str(step_output) if step_output is not None else ""
                    self.logger.debug("[EXEC] Raw response from '%s': %s", agent.agent_id, str(step_output)[:200])
                    
                    try:
                        # ── Short-circuit for AgentString with developer metadata ──
                        # DeveloperAgent returns an AgentString (str subclass) with a
                        # `.metadata` dict (files, preview_url, etc.).  If we let the
                        # JSON-parsing loop continue it would extract only the bare
                        # `result` string and discard all metadata.  Break out early.
                        from app.agents.developer import AgentString as _AgentString
                        if isinstance(step_output, _AgentString) and step_output.metadata:
                            output = step_output  # preserve AgentString + metadata
                            success = True
                            break

                        cleaned = step_output.strip()
                        if cleaned.startswith("```json"):
                            cleaned = cleaned[7:]
                        if cleaned.endswith("```"):
                            cleaned = cleaned[:-3]
                        cleaned = cleaned.strip()
                        
                        data = json.loads(cleaned)
                        if isinstance(data, dict) and data.get("tool_required"):
                            tool_id = data.get("tool")
                            arguments = data.get("arguments", {})
                            
                            # Check for duplicate tool call to prevent infinite loops
                            current_call = (tool_id, json.dumps(arguments, sort_keys=True))
                            if previous_tool_call == current_call:
                                self.logger.warning(
                                    "[EXEC] Duplicate tool call detected for '%s': %s — forcing final answer.",
                                    agent.agent_id, tool_id
                                )
                                # Force the agent to produce a final answer on the next call
                                forced_msg = (
                                    f"\n\n[SYSTEM OVERRIDE] The tool '{tool_id}' was already called with identical "
                                    f"arguments and returned no new data. You MUST stop calling tools and return "
                                    f"tool_required=false with your best final answer right now."
                                )
                                for key in ["task", "topic", "requirement", "target", "output", "movie_goal"]:
                                    if key in payload and payload[key]:
                                        payload[key] += forced_msg
                                        break
                                else:
                                    payload["task"] = payload.get("task", "") + forced_msg
                                attempt += 1
                                continue
                            
                            previous_tool_call = current_call
                            # Mark payload so agent.execute() implementations know we are
                            # in a tool-calling iteration (used to bypass semantic cache)
                            payload["_tool_iteration"] = attempt + 1
                            
                            # Execute the tool via ToolManager
                            from app.core.shared import tool_manager
                            print(f"[OS KERNEL INTERCEPT] Agent '{agent.agent_id}' calling tool '{tool_id}' with args {arguments}")
                            
                            tool_result = tool_manager.execute(tool_id, arguments, agent.agent_id)
                            self.logger.info("[EXEC] Tool '%s' result: %s", tool_id, str(tool_result)[:200])
                            
                            # If tool returns a stub, explicitly warn the LLM
                            if "Stub" in str(tool_result) or "not implemented" in str(tool_result).lower():
                                for key in ["task", "topic", "requirement", "target", "output", "movie_goal"]:
                                    if key in payload and payload[key]:
                                        payload[key] += (
                                            f"\n\nTool '{tool_id}' returned a stub/empty result:\n"
                                            f"{tool_result}\n"
                                            f"The tool has no additional information. Do not call '{tool_id}' again. "
                                            f"Return your final answer with tool_required=false based on available information.\n"
                                        )

                            # Record tool invocation in payload execution memory
                            if "history" not in payload:
                                payload["history"] = []
                            payload["history"].append({
                                "thought": data.get("thought"),
                                "tool": tool_id,
                                "arguments": arguments,
                                "result": tool_result
                            })
                            
                            # Update context in payload so when we call agent.execute again, it has the tool output
                            history_str = "\n".join([
                                f"Thought: {h['thought']}\nTool: {h['tool']}({h['arguments']}) -> Result: {h['result']}"
                                for h in payload["history"]
                            ])
                            
                            # Update all key fields so the template rendering picks it up
                            found_key = False
                            for key in ["task", "topic", "requirement", "target", "output", "movie_goal"]:
                                if key in payload and payload[key]:
                                    found_key = True
                                    orig_key = f"original_{key}"
                                    if orig_key not in payload:
                                        payload[orig_key] = payload[key]
                                    payload[key] = (
                                        f"{payload[orig_key]}\n\n"
                                        f"### Execution Memory / Tool History:\n"
                                        f"{history_str}\n\n"
                                        f"Please continue. If you have the final answer, return tool_required=false."
                                    )
                                    
                            if not found_key:
                                payload["task"] = (
                                    f"### Execution Memory / Tool History:\n"
                                    f"{history_str}\n\n"
                                    f"Please continue. If you have the final answer, return tool_required=false."
                                ) 

                            attempt += 1
                            continue
                        else:
                            # Finished! Extract the final answer
                            if isinstance(data, dict):
                                final_res = data.get("result")
                                if final_res is None:
                                    final_res = data.get("thought", step_output)
                                
                                if isinstance(final_res, (list, dict)):
                                    output = json.dumps(final_res)
                                else:
                                    output = str(final_res)
                            else:
                                output = step_output
                            break
                    except Exception:
                        # Fallback for plain text
                        output = step_output
                        break
                else:
                    raise RuntimeError("Agent exceeded maximum iterative tool executions limit (10).")
                
                success = True
            except Exception as exc:
                error = str(exc)
                self.logger.exception("Agent %s failed during run", agent.agent_id)


        duration = time.perf_counter() - start_time

        # Track memory usage after run
        mem_after = 0.0
        if psutil is not None:
            try:
                mem_after = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        # Calculate RSS RAM growth delta
        memory_used = max(0.0, mem_after - mem_before)

        result = ExecutionResult(
            success=success,
            output=output,
            error=error,
            agent_id=agent.agent_id,
            stdout=stdout_buf.getvalue(),
            stderr=stderr_buf.getvalue(),
            duration_seconds=duration,
            memory_used_mb=memory_used,
        )

        self._record_execution(agent.agent_id, result)
        return result

    def execute_sequential(self, agents: list[BaseAgent], payloads: list[dict[str, Any] | None] | None = None) -> list[ExecutionResult]:
        """Execute a list of agents one after another."""
        payloads = payloads or [None] * len(agents)
        return [self.execute_agent(agent, payload) for agent, payload in zip(agents, payloads)]

    def execute_parallel(self, agents: list[BaseAgent], payloads: list[dict[str, Any] | None] | None = None) -> list[ExecutionResult]:
        """Execute a list of agents in parallel using the configured max concurrency."""
        payloads = payloads or [None] * len(agents)
        workers = self._max_workers or max(1, len(agents))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(self.execute_agent, agent, payload) for agent, payload in zip(agents, payloads)]
            return [future.result() for future in futures]

    def enqueue_task(self, agent: BaseAgent, payload: dict[str, Any] | None = None) -> None:
        """Queue a task for later dispatch."""
        self._queue.append((agent, payload))
        self._processes[agent.agent_id] = {"agent_id": agent.agent_id, "status": "queued", "payload": payload}

    def dispatch_next(self) -> ExecutionResult:
        """Dispatch the next queued task."""
        if not self._queue:
            raise IndexError("Execution queue is empty")
        agent, payload = self._queue.popleft()
        self._processes[agent.agent_id] = {"agent_id": agent.agent_id, "status": "running", "payload": payload}
        result = self.execute_agent(agent, payload)
        self._processes[agent.agent_id] = {"agent_id": agent.agent_id, "status": "completed" if result.success else "failed", "payload": payload}
        return result

    def queue_size(self) -> int:
        """Return the number of queued tasks."""
        return len(self._queue)

    def get_processes(self) -> list[dict[str, Any]]:
        """Return currently tracked process metadata."""
        return list(self._processes.values())

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Return execution history entries."""
        return list(self._history)

    def get_metrics(self) -> dict[str, int]:
        """Return runtime metrics."""
        return dict(self._metrics)

    def _record_execution(self, agent_id: str, result: ExecutionResult) -> None:
        self._metrics["total_executions"] += 1
        if result.success:
            self._metrics["success_count"] += 1
        else:
            self._metrics["failure_count"] += 1
        self._history.append(
            {
                "agent_id": agent_id,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "timestamp": result.timestamp,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_seconds": result.duration_seconds,
                "memory_used_mb": result.memory_used_mb,
            }
        )
