"""Microkernel orchestrator representing the core runtime of AgentSphere OS v4."""

import asyncio
from typing import Any, Optional, Dict, List
from app.runtime.process_manager import ProcessManager
from app.core.logging import get_logger

logger = get_logger("agentsphere.kernel")


class Microkernel:
    """Orchestrates system startup, task routing, resource constraints, and process lifecycle controls."""

    def __init__(self, process_manager: ProcessManager) -> None:
        self.process_manager = process_manager
        self.is_booted = False

        # Resource limits and constraints config
        self.max_concurrency = 4
        self.max_tool_calls = 50
        self.api_budget = 10.0  # in USD
        self.memory_limit_mb = 4096.0  # 4 GB — realistic limit for a server process running LLMs
        self.timeout_seconds = 120.0

    def set_resource_limits(
        self,
        max_concurrency: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        api_budget: Optional[float] = None,
        memory_limit_mb: Optional[float] = None,
        timeout_seconds: Optional[float] = None
    ) -> None:
        """Dynamically configure microkernel execution and resource constraints."""
        if max_concurrency is not None:
            self.max_concurrency = max_concurrency
            try:
                from app.core.shared import scheduler, execution_engine
                scheduler.max_concurrency = max_concurrency
                execution_engine.set_concurrency_limit(max_concurrency)
            except ImportError:
                pass
        if max_tool_calls is not None:
            self.max_tool_calls = max_tool_calls
        if api_budget is not None:
            self.api_budget = api_budget
        if memory_limit_mb is not None:
            self.memory_limit_mb = memory_limit_mb
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        logger.info(
            "Resource limits updated: concurrency=%s, tools=%s, budget=%s, memory=%s, timeout=%s",
            max_concurrency, max_tool_calls, api_budget, memory_limit_mb, timeout_seconds
        )

    def check_api_budget(self) -> None:
        """Ensure current API calls cost does not exceed budget limits."""
        try:
            from app.core.shared import model_router
            current_cost = model_router.get_usage_metrics().get("total_cost", 0.0)
            if current_cost > self.api_budget:
                raise RuntimeError(
                    f"Execution blocked: API budget ({self.api_budget} USD) exceeded. "
                    f"Current cost: {current_cost:.4f} USD."
                )
        except ImportError:
            pass

    def _classify_workflow(self, task: str) -> str:
        """Analyze a natural language task description to select the appropriate workflow route."""
        t = task.lower()
        if any(w in t for w in ["documentary", "history", "factual"]):
            return "documentary"
        if any(w in t for w in ["podcast", "interview", "audio show"]):
            return "podcast"
        if any(w in t for w in ["ad", "advertisement", "commercial", "promo"]):
            return "advertisement"
        if any(w in t for w in ["game trailer", "gaming trailer"]):
            return "game trailer"
        if any(w in t for w in ["music video", "song video"]):
            return "music video"
        if any(w in t for w in ["rest api", "code", "dev", "build", "api", "software", "test", "coding", "python", "javascript", "typescript", "c++", "c#", "java"]):
            return "coding"
        # Default fallback is Movie production
        return "movie"

    async def execute(self, task: str, workflow: Optional[str] = None) -> Any:
        """Choose workflow, execute sequential/parallel agent processes, and return final output."""
        import asyncio
        import json
        from app.core.shared import supervisor, event_bus, checkpoint_manager, shared_memory
        
        self.check_api_budget()

        # 1. Classify workflow if none provided
        if workflow is None:
            workflow = self._classify_workflow(task)

        logger.info("Kernel executing task: '%s' via workflow: '%s'", task, workflow)
        
        # Publish start event
        event_bus.publish("workflow.started", {"task": task, "workflow": workflow})

        # Query persistent long-term vector context (Phase 5: Persistent Memory)
        restored_context = ""
        try:
            past_memories = await shared_memory.query_vector(task, top_k=2)
            if past_memories:
                memory_lines = []
                for m in past_memories:
                    if m.get("similarity", 0.0) > 0.25:
                        memory_lines.append(
                            f"- Past task '{m['text']}' completed with result summary:\n"
                            f"  {str(m['metadata'].get('result'))[:300]}"
                        )
                if memory_lines:
                    restored_context = (
                        "### RESTORED CONTEXT MEMORIES (Long-Term Project Memory):\n" +
                        "\n".join(memory_lines) + "\n\n"
                    )
                    logger.info("Kernel successfully restored long-term memory context for task.")
        except Exception as e:
            logger.warning(f"Failed to query vector memory context: {e}")

        # 2. Retrieve steps
        if workflow == "coding":
            steps = [
                ("planner", "Planner Task", "Planner"),
                ("parallel:researcher,developer", "Parallel Researchers and Developers Task", "Parallel Sub-Agents"),
                ("tester", "Tester Task", "Tester"),
                ("reviewer", "Reviewer Task", "Reviewer")
            ]
        else:
            from app.runtime.workflow_engine import WorkflowEngine
            steps = WorkflowEngine.get_steps(workflow)

        previous_output = None
        results = {}

        # 3. Step execution loop
        for agent_id, task_name, display_name in steps:
            self.check_api_budget()

            # Handle generic parallel block (Phase 3: Multi-Agent Parallelism)
            if isinstance(agent_id, str) and agent_id.startswith("parallel:"):
                agents_to_run = agent_id[9:].split(",")
                
                async def run_parallel_subagent(sub_agent_id: str) -> tuple[str, Any]:
                    p_payload = {
                        "task": task,
                        "topic": task,
                        "requirement": previous_output or task,
                        "context": previous_output,
                    }
                    if restored_context:
                        p_payload["context_restored"] = restored_context
                        p_payload["requirement"] = restored_context + p_payload["requirement"]
                    
                    p_task_id = await supervisor.assign_task(
                        name=f"Parallel {sub_agent_id}", agent_id=sub_agent_id, payload=p_payload
                    )
                    checkpoint_manager.create_checkpoint(
                        task_id=p_task_id,
                        name=f"Pre-{sub_agent_id}",
                        state={"payload": p_payload, "memory": shared_memory.snapshot()}
                    )
                    p_res = await supervisor.run_task(p_task_id)
                    if not p_res.success:
                        raise RuntimeError(f"Parallel step failed for agent {sub_agent_id}: {p_res.error}")
                    return sub_agent_id, p_res.output

                logger.info(f"Executing parallel subagents: {agents_to_run}")
                event_bus.publish("workflow.parallel_started", {"agents": agents_to_run})

                parallel_results = await asyncio.gather(
                    *[run_parallel_subagent(aid) for aid in agents_to_run]
                )

                # Merge outputs
                merged_output = "\n\n=== PARALLEL EXECUTION MERGED OUTPUT ===\n"
                for aid, out in parallel_results:
                    merged_output += f"\n--- Output of {aid.upper()} ---\n{out}\n"
                    results[aid] = out
                previous_output = merged_output
                continue

            # Handle legacy showrunner parallel block
            if agent_id == "showrunner_parallel":
                parallel_agents = [
                    ("showrunner_script", "Script Task"),
                    ("showrunner_storyboard", "Storyboard Task"),
                    ("showrunner_researcher", "Brand Research"),
                    ("showrunner_voice", "Voice Selection"),
                ]

                async def run_parallel_step(p_agent_id: str, p_task_name: str) -> tuple[str, Any]:
                    p_payload = {
                        "task": task,
                        "movie_goal": task,
                        "context": previous_output,
                    }
                    if restored_context:
                        p_payload["context_restored"] = restored_context
                    p_task_id = await supervisor.assign_task(
                        name=p_task_name, agent_id=p_agent_id, payload=p_payload
                    )
                    checkpoint_manager.create_checkpoint(
                        task_id=p_task_id,
                        name=f"Pre-{p_agent_id}",
                        state={"payload": p_payload, "memory": shared_memory.snapshot()}
                    )
                    p_res = await supervisor.run_task(p_task_id)
                    if not p_res.success:
                        raise RuntimeError(f"Parallel step failed for agent {p_agent_id}: {p_res.error}")
                    return p_agent_id, p_res.output

                logger.info("Executing parallel step block: %s", display_name)
                event_bus.publish("workflow.parallel_started", {"agents": [a[0] for a in parallel_agents]})

                parallel_results = await asyncio.gather(
                    *[run_parallel_step(p_aid, p_tname) for p_aid, p_tname in parallel_agents]
                )

                for p_aid, p_out in parallel_results:
                    results[p_aid] = p_out
                # Default previous output to script agent's output
                previous_output = results.get("showrunner_script", previous_output)
                continue

            # Standard sequential step
            payload = {
                "task": task,
                "movie_goal": task,
                "topic": task,
                "requirement": task,
                "target": task,
                "output": task,
            }
            if restored_context:
                payload["context_restored"] = restored_context
                for k in ["task", "topic", "requirement"]:
                    if k in payload:
                        payload[k] = restored_context + payload[k]

            if previous_output:
                payload["context"] = previous_output
                payload["input"] = previous_output
                if agent_id == "developer":
                    payload["requirement"] = previous_output
                elif agent_id == "tester":
                    payload["target"] = previous_output
                elif agent_id == "reviewer":
                    payload["output"] = previous_output

            event_bus.publish("agent.started", {"agent_id": agent_id, "task_name": task_name})

            # Submit/Assign and execute
            task_id = await supervisor.assign_task(name=task_name, agent_id=agent_id, payload=payload)

            # Persist checkpoint before executing
            checkpoint_manager.create_checkpoint(
                task_id=task_id,
                name=f"Pre-{agent_id}",
                state={"payload": payload, "memory": shared_memory.snapshot()}
            )

            try:
                if self.timeout_seconds:
                    res = await asyncio.wait_for(supervisor.run_task(task_id), timeout=self.timeout_seconds)
                else:
                    res = await supervisor.run_task(task_id)
            except asyncio.TimeoutError:
                event_bus.publish("agent.failed", {"agent_id": agent_id, "error": "Timeout exceeded"})
                raise TimeoutError(f"Agent '{agent_id}' execution timed out after {self.timeout_seconds} seconds.")

            # Apply recovery if step fails
            if not res.success:
                event_bus.publish("agent.failed", {"agent_id": agent_id, "error": res.error})
                from app.core.shared import recovery_engine
                t_model = supervisor.get_task(task_id)
                recovered = await recovery_engine.recover_task(t_model, supervisor)
                if recovered:
                    logger.info("Recovery Engine: Restored checkpoint and resumed agent '%s'.", agent_id)
                    res = await supervisor.run_task(task_id)

                if not res.success:
                    raise RuntimeError(f"Workflow execution failed at agent '{agent_id}': {res.error}")

            previous_output = res.output
            results[agent_id] = res.output
            event_bus.publish("agent.completed", {"agent_id": agent_id, "output": res.output})

        # Store completed task result in long-term vector database (Phase 5: Persistent Memory)
        try:
            await shared_memory.add_vector(
                text=task,
                metadata={"result": previous_output, "workflow": workflow}
            )
            logger.info("Successfully registered task completion outcome into vector database.")
        except Exception as e:
            logger.warning(f"Failed to save task vector memory: {e}")

        event_bus.publish("workflow.completed", {"task": task, "workflow": workflow, "result": previous_output})
        return previous_output

    # ---------------------------------------------------------------------------
    # Agent Lifecycle Management Wrappers
    # ---------------------------------------------------------------------------

    async def create_agent_process(self, agent_id: str, name: str, metadata: Optional[dict] = None) -> str:
        """Create and register a new process associated with an agent."""
        proc = await self.process_manager.create_process(
            name=name,
            metadata={**(metadata or {}), "agent_id": agent_id}
        )
        return proc.process_id

    async def start_agent_process(self, pid: str) -> bool:
        """Transition process to running status."""
        return await self.process_manager.start_process(pid)

    async def pause_agent_process(self, pid: str) -> bool:
        """Suspend running process execution."""
        return await self.process_manager.suspend_process(pid)

    async def resume_agent_process(self, pid: str) -> bool:
        """Resume suspended process execution."""
        return await self.process_manager.resume_process(pid)

    async def terminate_agent_process(self, pid: str) -> bool:
        """Terminate (kill) a process."""
        return await self.process_manager.kill_process(pid)

    async def restart_agent_process(self, pid: str) -> str:
        """Restart a process by spawning a new one with matching configuration."""
        proc = await self.process_manager.repository.get(pid)
        if not proc:
            raise KeyError(f"Process '{pid}' not found.")
        await self.terminate_agent_process(pid)
        new_proc = await self.process_manager.create_process(name=proc.name, metadata=proc.metadata)
        await self.process_manager.start_process(new_proc.process_id)
        return new_proc.process_id

    # ---------------------------------------------------------------------------
    # System Boot
    # ---------------------------------------------------------------------------

    async def boot(self) -> None:
        """Start the microkernel execution runtime and prepare systems."""
        if self.is_booted:
            logger.warning("Microkernel boot sequence called on already running kernel")
            return

        logger.info("Starting Microkernel subsystem boot sequence...")
        
        # Subsystem initialization hook points
        # Load Showrunner plugins dynamically
        try:
            from app.core.shared import plugin_manager, supervisor
            
            showrunner_agents = [
                ("app.plugins.showrunner.planner", "ShowrunnerPlannerAgent", "showrunner_planner"),
                ("app.plugins.showrunner.researcher_agent", "ShowrunnerResearchAgent", "showrunner_researcher"),
                ("app.plugins.showrunner.script_agent", "ShowrunnerScriptAgent", "showrunner_script"),
                ("app.plugins.showrunner.storyboard_agent", "ShowrunnerStoryboardAgent", "showrunner_storyboard"),
                ("app.plugins.showrunner.scene_agent", "ShowrunnerSceneAgent", "showrunner_scene"),
                ("app.plugins.showrunner.prompt_agent", "ShowrunnerPromptAgent", "showrunner_prompt"),
                ("app.plugins.showrunner.video_agent", "ShowrunnerVideoAgent", "showrunner_video"),
                ("app.plugins.showrunner.voice_agent", "ShowrunnerVoiceAgent", "showrunner_voice"),
                ("app.plugins.showrunner.audio_agent", "ShowrunnerAudioAgent", "showrunner_audio"),
                ("app.plugins.showrunner.subtitle_agent", "ShowrunnerSubtitleAgent", "showrunner_subtitle"),
                ("app.plugins.showrunner.editor_agent", "ShowrunnerEditorAgent", "showrunner_editor"),
                ("app.plugins.showrunner.reviewer_agent", "ShowrunnerReviewerAgent", "showrunner_reviewer"),
                ("app.plugins.showrunner.director_agent", "ShowrunnerDirectorAgent", "showrunner_director"),
                ("app.plugins.showrunner.poster_generator", "ShowrunnerPosterAgent", "showrunner_poster"),
                ("app.plugins.showrunner.trailer_generator", "ShowrunnerTrailerAgent", "showrunner_trailer"),
                ("app.plugins.showrunner.publishing_agent", "ShowrunnerPublishingAgent", "showrunner_publisher"),
                ("app.plugins.showrunner.report_generator", "ShowrunnerReportAgent", "showrunner_reporter"),
            ]
            
            for module_path, class_name, agent_id in showrunner_agents:
                try:
                    plugin_manager.load_agent_plugin(module_path, class_name, agent_id)
                    # Instantiate and register with supervisor
                    agent = plugin_manager.create_agent(agent_id)
                    supervisor.register_agent(agent)
                    logger.info(f"Dynamically hot-loaded showrunner agent: {agent_id}")
                except Exception as ex:
                    logger.error(f"Failed to dynamically load showrunner agent {agent_id}: {ex}")
        except Exception as e:
            logger.error(f"Error initializing plugins on kernel boot: {e}")

        self.is_booted = True
        self._resource_monitor_task = asyncio.create_task(self._resource_monitor_loop())
        logger.info("AgentSphere OS Microkernel booted successfully.")

    async def shutdown(self) -> None:
        """Gracefully shut down the microkernel systems."""
        if not self.is_booted:
            return
        self.is_booted = False
        if hasattr(self, "_resource_monitor_task") and self._resource_monitor_task:
            self._resource_monitor_task.cancel()
            try:
                await self._resource_monitor_task
            except asyncio.CancelledError:
                pass
            self._resource_monitor_task = None
        logger.info("AgentSphere OS Microkernel shut down successfully.")

    async def _resource_monitor_loop(self, once: bool = False) -> None:
        """Background loop monitoring system resource limits, enforcing safety thresholds."""
        from app.core.shared import model_router, process_manager, checkpoint_manager, shared_memory, supervisor
        from app.models.process import ProcessStatus
        import os
        
        while self.is_booted:
            try:
                # 1. Gather RAM & CPU metrics
                try:
                    import psutil
                    proc = psutil.Process(os.getpid())
                    cpu = psutil.cpu_percent(interval=None)
                    memory_mb = proc.memory_info().rss / (1024 * 1024)
                except ImportError:
                    cpu = 5.0
                    memory_mb = 110.0

                # 2. Check resource limits
                cost = model_router.get_usage_metrics().get("total_cost", 0.0)
                if cost > self.api_budget:
                    logger.error(f"[OOM/BUDGET MONITOR] API Budget exceeded ({cost} > {self.api_budget}). Suspending running processes.")
                    running_procs = [p for p in await process_manager.list_processes() if p.status == ProcessStatus.RUNNING]
                    for p in running_procs:
                        await self.pause_agent_process(p.process_id)
                        checkpoint_manager.create_checkpoint(p.process_id, "BudgetExceeded", {"status": "suspended"})
                
                if memory_mb > self.memory_limit_mb:
                    logger.error(
                        "[OOM/BUDGET MONITOR] Memory Limit exceeded (%.1fMB > %.0fMB). "
                        "Consider increasing kernel.memory_limit_mb or reducing payload sizes.",
                        memory_mb, self.memory_limit_mb
                    )
                    # Log but do NOT kill running processes — killing a process mid-LLM-call
                    # corrupts the execution state and causes 500 errors on the API response.
                    # The old code called terminate + restart which created a new orphan process
                    # while the task still pointed to the killed PID.
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
            
            if once:
                break
            await asyncio.sleep(2.0)


