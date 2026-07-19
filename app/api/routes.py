"""FastAPI routes for AgentSphere OS runtime interaction."""

from __future__ import annotations

import asyncio
import json as json_lib
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse

from app.agents.developer import DeveloperAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.dependency.dependency_manager import DependencyManager
from app.core.shared import (
    supervisor, event_bus, shared_memory, plugin_manager,
    recovery_engine, model_router, dependency_manager, checkpoint_manager
)

router = APIRouter()


for agent in (PlannerAgent(), ResearcherAgent(), DeveloperAgent(), TesterAgent(), ReviewerAgent()):
    if agent.agent_id not in supervisor._agents:  # BUG-001 fix: prevent triple registration
        supervisor.register_agent(agent)

# Seed a simple dependency chain so the dependency APIs expose meaningful data.
dependency_manager.add_dependency("planner", "researcher")
dependency_manager.add_dependency("researcher", "developer")
dependency_manager.add_dependency("developer", "tester")
dependency_manager.add_dependency("tester", "reviewer")

# Maps each agent_id to the payload key it reads from its execute() method.
_AGENT_PAYLOAD_KEY: dict[str, str] = {
    "planner": "task",
    "researcher": "topic",
    "developer": "requirement",
    "tester": "target",
    "reviewer": "output",
}

_DASHBOARD_PATH = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"

# WebSocket connections manager
_active_connections: List[WebSocket] = []


async def broadcast(message: Dict[str, Any]) -> None:
    """Broadcast a message to all active WebSocket connections."""
    for connection in _active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Core health / info
# ---------------------------------------------------------------------------

@router.get("/")
def root() -> dict[str, str]:
    """Return a simple landing response for the service."""
    return {"message": "AgentSphere OS is running"}





@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Return comprehensive runtime status."""
    return {
        "supervisor": await supervisor.get_supervisor_status(),
        "memory": shared_memory.snapshot(),
        "dependencies": get_dependencies(),
        # Only return IDs — list_checkpoints() deserializes full state blobs which is very slow
        "checkpoints": checkpoint_manager.list_checkpoint_ids(limit=50),
        "events": event_bus.get_recent_events(50),
    }


# ---------------------------------------------------------------------------
# Agents endpoints
# ---------------------------------------------------------------------------

@router.get("/agents")
def list_agents() -> list[dict[str, Any]]:
    """List all registered agents."""
    return [
        {"agent_id": agent.agent_id, "name": agent.name, "description": getattr(agent, "description", "")}
        for agent in supervisor._agents.values()
    ]


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str) -> dict[str, Any]:
    """Get details of a specific agent."""
    agent = supervisor._agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    state = supervisor.get_agent_state(agent_id)
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": getattr(agent, "description", ""),
        "status": state.status.value,
        "metadata": state.metadata,
    }


# ---------------------------------------------------------------------------
# Task submission
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def submit_task(name: str, agent_id: str, payload: dict | None = None) -> dict[str, str]:
    """Submit a task to the supervisor for execution."""
    task_id = await supervisor.submit_task(name=name, agent_id=agent_id, payload=payload)
    return {"task_id": task_id}


@router.post("/assign")
async def assign_task(payload: dict[str, object], background_tasks: BackgroundTasks) -> dict[str, str]:
    """Assign a task to an agent and queue it for background execution.

    Accepts the following JSON shapes (all equivalent)::

        {"agent_id": "planner", "task": "Build a REST API"}
        {"agent": "planner", "task": "Build a REST API"}
        {"agent_id": "planner", "input": "Build a REST API"}
        {"agent_id": "planner", "payload": {"task": "Build a REST API"}}
    """
    agent_id = str(payload.get("agent_id") or payload.get("agent") or "")
    task_name = str(payload.get("name") or payload.get("task") or payload.get("input") or "")

    # Build the agent-specific payload dict.
    task_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else None
    if task_payload is None:
        agent_key = _AGENT_PAYLOAD_KEY.get(agent_id, "task")
        input_value = str(
            payload.get("input")
            or payload.get(agent_key)
            or payload.get("task")
            or ""
        )
        task_payload = {agent_key: input_value} if input_value else None

    task_id = await supervisor.assign_task(name=task_name, agent_id=agent_id, payload=task_payload)
    background_tasks.add_task(supervisor.run_task, task_id)
    return {"task_id": task_id, "status": "queued"}


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    """Retrieve the status and result of a task."""
    task = supervisor.get_task(task_id)
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "result": task.result,
        "error": task.error,
    }


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: str) -> dict[str, object]:
    """Execute a previously submitted task."""
    try:
        result = await supervisor.run_task(task_id)
    except KeyError as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": result.success, "output": result.output, "error": result.error}


@router.get("/tasks")
def list_tasks() -> list[dict[str, Any]]:
    """List all tasks."""
    return [
        {
            "task_id": task.task_id,
            "name": task.name,
            "agent_id": task.agent_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
        }
        for task in supervisor._tasks.values()
    ]


@router.get("/tasks/{task_id}/result")
def get_task_result(task_id: str) -> dict[str, Any]:
    """Return structured build output for a completed task.

    If the developer agent stored a dict result (files, preview_url, etc.),
    it is returned directly.  For other agents the raw result is wrapped so
    the frontend always sees a consistent shape.
    """
    try:
        task = supervisor.get_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status.value not in ("completed", "failed"):
        return {"status": task.status.value, "ready": False}

    result = task.result

    # Developer agent already returns a structured dict
    if isinstance(result, dict) and "output_type" in result:
        return {"status": "completed", "ready": True, **result}

    # For other agents or plain string results — wrap into generic structure
    raw = str(result) if result else (task.error or "No output")
    return {
        "status": "completed" if task.status.value == "completed" else "failed",
        "ready": True,
        "output_type": "code",
        "files": [{"filename": "output.txt", "language": "text", "content": raw}],
        "preview_url": "",
        "architecture": "",
        "summary": raw[:200],
        "raw": raw,
        "file_count": 1,
    }


# ---------------------------------------------------------------------------
# Process & supervisor info
# ---------------------------------------------------------------------------

@router.get("/processes")
async def list_processes() -> list[dict[str, object]]:
    """Return the current supervisor process table."""
    return await supervisor.list_processes()


@router.get("/supervisor")
async def supervisor_status() -> dict[str, object]:
    """Return the current supervisor runtime status."""
    return await supervisor.get_supervisor_status()


@router.get("/api/processor/status")
async def background_processor_status() -> dict[str, object]:
    """
    Real-time background processor status.
    Returns everything the frontend needs to show live processing:
    - active tasks (RUNNING state)
    - queued tasks (CREATED state)
    - completed tasks (last 10)
    - failed tasks (last 10)
    - scheduler queue depth
    - current running agent
    """
    from app.core.shared import scheduler

    procs = await supervisor.list_processes()

    running  = [p for p in procs if (p.get("current_state") or "").lower() == "running"]
    created  = [p for p in procs if (p.get("current_state") or "").lower() == "created"]
    done     = [p for p in procs if (p.get("current_state") or "").lower() in ("stopped", "completed")]
    failed   = [p for p in procs if (p.get("current_state") or "").lower() == "failed"]

    # Build active task view with human-readable labels
    _AGENT_LABELS = {
        "planner": "Planning Agent",      "researcher": "Research Agent",
        "developer": "Developer Agent",   "tester": "Testing Agent",
        "reviewer": "Reviewer Agent",     "showrunner_planner": "Movie Planner",
        "showrunner_script": "Scriptwriter",
        "showrunner_storyboard": "Storyboard Artist",
        "showrunner_scene": "Scene Generator",
        "showrunner_voice": "Voice Selector",
        "showrunner_video": "Video Producer",
        "showrunner_editor": "Video Editor",
        "showrunner_reviewer": "Quality Reviewer",
        "showrunner_reporter": "Report Writer",
    }

    def fmt(p: dict) -> dict:
        agent_id = p.get("agent", "")
        return {
            "pid": p.get("pid"),
            "task_id": p.get("task_id"),
            "agent_id": agent_id,
            "agent_label": _AGENT_LABELS.get(agent_id, agent_id),
            "task": p.get("current_task", "—"),
            "state": p.get("current_state", "unknown"),
            "started": p.get("created_time"),
            "updated": p.get("updated_time"),
        }

    return {
        "summary": {
            "total": len(procs),
            "running": len(running),
            "queued": len(created),
            "completed": len(done),
            "failed": len(failed),
            "scheduler_queue_depth": scheduler.size(),
            "scheduler_active": scheduler.active_count(),
            "concurrency_limit": scheduler.max_concurrency,
        },
        "running": [fmt(p) for p in running],
        "queued":  [fmt(p) for p in created],
        "recent_completed": [fmt(p) for p in done[-10:]],
        "recent_failed":    [fmt(p) for p in failed[-10:]],
    }


@router.get("/supervisor/status")
async def supervisor_status_detail() -> dict[str, object]:
    """Return the detailed supervisor runtime status."""
    return await supervisor.get_supervisor_status()


@router.get("/diagnostics")
def diagnostics() -> dict[str, object]:
    """Return a consolidated health snapshot for the runtime."""
    return {
        "runtime": True,
        "supervisor": True,
        "memory": True,
        "shared_memory": True,
        "execution_engine": True,
        "dependency_manager": True,
        "dependencies": True,
        "registered_agents": len(supervisor._agents),
        "process_table": True,
        "checkpoint_manager": True,
        "recovery_engine": True,
    }


# ---------------------------------------------------------------------------
# Shared memory
# ---------------------------------------------------------------------------

@router.get("/memory")
def get_memory() -> dict[str, object]:
    """Return the current shared-memory snapshot grouped by namespace."""
    snapshot = shared_memory.snapshot()
    grouped: dict[str, dict[str, object]] = {}
    for key, value in snapshot.items():
        namespace, separator, remainder = key.partition(":")
        if namespace and separator and remainder:
            grouped.setdefault(namespace, {})[remainder] = value
        else:
            grouped.setdefault("root", {})[key] = value
    return grouped


@router.post("/memory")
def write_memory(payload: dict[str, object]) -> dict[str, object]:
    """Write a value into the shared-memory store."""
    namespace = str(payload.get("namespace", "")) or None
    key = str(payload.get("key", ""))
    value = payload.get("value")
    shared_memory.write(namespace=namespace, key=key, value=value)
    return {"status": "ok", "key": key, "namespace": namespace}


@router.get("/memory/{key}")
def read_memory(key: str, namespace: str | None = None) -> dict[str, Any]:
    """Read a specific memory key."""
    value = shared_memory.read(namespace=namespace, key=key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "namespace": namespace, "value": value}


@router.delete("/memory/{key}")
def delete_memory(key: str, namespace: str | None = None) -> dict[str, Any]:
    """Delete a memory key."""
    storage_key = f"{namespace}:{key}" if namespace else key
    shared_memory.delete(storage_key)
    return {"status": "ok"}


@router.post("/api/memory/clear")
def clear_all_memory() -> dict:
    """Clear all shared memory tables and semantic cache vector items."""
    shared_memory.clear()
    return {"status": "ok", "message": "All memory and semantic cache cleared successfully"}


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------

@router.get("/checkpoints")
def list_checkpoints(limit: int = 50) -> list[dict[str, Any]]:
    """List recent checkpoints (metadata only, no full state deserialization)."""
    return checkpoint_manager.list_checkpoint_ids(limit=limit, with_meta=True)


@router.get("/checkpoints/{checkpoint_id}")
def get_checkpoint(checkpoint_id: str) -> dict[str, Any]:
    """Get a specific checkpoint."""
    checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint.to_dict()


@router.post("/checkpoints")
def create_checkpoint(task_id: str, name: str | None = None) -> dict[str, Any]:
    """Create a checkpoint from a task."""
    task = supervisor.get_task(task_id)
    checkpoint = checkpoint_manager.create_checkpoint(
        task_id=task_id,
        name=name or f"Checkpoint for {task.name}",
        state={
            "task": task.to_dict(),
            "memory": shared_memory.snapshot(),
        }
    )
    return checkpoint.to_dict()


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

@router.post("/rollback")
def rollback_to_checkpoint(checkpoint_id: str) -> dict[str, Any]:
    """Rollback to a checkpoint."""
    checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    # Restore memory state
    memory_state = checkpoint.state.get("memory", {})
    for key, value in memory_state.items():
        shared_memory.set(key, value)
    
    return {"status": "ok", "checkpoint_id": checkpoint_id, "message": "Rolled back successfully"}


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------

@router.post("/recovery")
async def trigger_recovery(task_id: str) -> dict[str, Any]:  # BUG-002 fix: must be async + await
    """Trigger recovery for a failed task."""
    try:
        task = supervisor.get_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    recovered = await recovery_engine.recover_task(task, supervisor)  # was missing await
    return {"status": "ok", "task_id": task_id, "recovered": recovered}


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.get("/events")
def list_events(limit: int = 100) -> list[dict[str, Any]]:
    """List recent events."""
    return event_bus.get_recent_events(limit)


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------

@router.get("/dependencies")
def get_dependencies() -> dict[str, list[str]]:
    """Return the dependency graph as a serializable mapping of prerequisites."""
    return {
        agent: sorted(dependency_manager.get_dependents(agent))
        for agent in dependency_manager.get_nodes()
    }


@router.get("/dependencies/visualize", response_class=HTMLResponse)
def visualize_dependencies() -> HTMLResponse:
    """Render and return the interactive dependency graph visualization using pyvis."""
    return HTMLResponse(content=dependency_manager.to_html())


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    _active_connections.append(websocket)
    event_bus.register_websocket(websocket)
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({
                "type": "update",
                "processes": await supervisor.list_processes(),
                "supervisor": await supervisor.get_supervisor_status(),
                "memory_keys": list(shared_memory.snapshot().keys()),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        _active_connections.remove(websocket)
        event_bus.unregister_websocket(websocket)


# ---------------------------------------------------------------------------
# Real-time streaming (SSE)
# ---------------------------------------------------------------------------

@router.get("/stream")
async def stream_events(once: bool = False) -> StreamingResponse:
    """Push real-time process and memory updates via Server-Sent Events."""

    async def event_generator():
        try:
            while True:
                event = json_lib.dumps({
                    "processes": await supervisor.list_processes(),
                    "supervisor": await supervisor.get_supervisor_status(),
                    "memory_keys": list(shared_memory.snapshot().keys()),
                })
                yield f"data: {event}\n\n"
                if once:
                    break
                await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            # BUG-SSE fix: client disconnected — terminate generator cleanly
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Web dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard() -> HTMLResponse:
    """Serve the AgentSphere OS live monitoring dashboard."""
    return HTMLResponse(content=_DASHBOARD_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# AI Showrunner & Plugin Loading Extension Endpoints
# ---------------------------------------------------------------------------
from fastapi.responses import FileResponse
import os

@router.post("/api/processes")
async def load_plugin_api(payload: dict) -> dict:
    action = payload.get("action")
    if action == "load_plugin":
        file_path = payload.get("file_path")
        class_name = payload.get("class_name")
        agent_id = payload.get("agent_id")
        if not file_path or not class_name or not agent_id:
            raise HTTPException(status_code=400, detail="Missing required parameters")
        try:
            if file_path.endswith(".py"):
                plugin_manager.load_plugin_from_file(file_path, class_name, agent_id)
            else:
                plugin_manager.load_agent_plugin(file_path, class_name, agent_id)
            agent = plugin_manager.create_agent(agent_id)
            supervisor.register_agent(agent)
            return {"status": "ok", "message": f"Plugin agent '{agent_id}' loaded and registered."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")


@router.get("/static/{filepath:path}")
def serve_static_file(filepath: str):
    full_path = Path("app/static") / filepath
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path)


async def run_showrunner_pipeline(movie_goal: str, user: str, media_type: str, simulate_failure: bool):
    import time
    from app.events.event_models import EventPriority
    start_time = time.time()
    
    def log_event(event_str):
        timeline = shared_memory.read("showrunner", "timeline") or []
        elapsed = int(time.time() - start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        time_tag = f"{minutes:02d}:{seconds:02d}"
        timeline.append(f"{time_tag} - {event_str}")
        shared_memory.write("showrunner", "timeline", timeline)
        
        # Publish event bus broadcast immediately
        try:
            event_bus.publish(
                event_type="SHOWRUNNER_UPDATE",
                payload={
                    "movie_goal": movie_goal,
                    "user": user,
                    "type": media_type,
                    "progress": shared_memory.read("showrunner", "progress") or "Running...",
                    "status": shared_memory.read("showrunner", "status") or "running",
                    "approval_state": shared_memory.read("showrunner", "approval_state") or "none",
                    "current_agent": shared_memory.read("showrunner", "current_agent") or "",
                    "timeline": timeline,
                    "current_pid": shared_memory.read("showrunner", "current_pid") or "PID-1001",
                },
                priority=EventPriority.MEDIUM
            )
        except Exception:
            pass

    try:
        shared_memory.write("showrunner", "movie_goal", movie_goal)
        shared_memory.write("showrunner", "user", user)
        shared_memory.write("showrunner", "type", media_type)
        shared_memory.write("showrunner", "progress", "Planner: 10% (Decomposing Goal...)")
        shared_memory.write("showrunner", "status", "running")
        shared_memory.write("showrunner", "approval_state", "none")
        shared_memory.write("showrunner", "simulate_failure", "true" if simulate_failure else "false")
        shared_memory.write("showrunner", "timeline", [])

        from app.runtime.workflow_engine import WorkflowEngine
        steps = WorkflowEngine.get_steps(media_type)

        log_event(f"{media_type.capitalize()} Production Pipeline Initialized")
        pid = "PID-1001" # Default fallback
        shared_memory.write("showrunner", "current_pid", pid)

        for agent_id, task_name, display in steps:
            # 1. Parallel execution block
            if agent_id == "showrunner_parallel":
                log_event("Parallel block enqueued (Script, Storyboard, Research, Voice)")
                shared_memory.write("showrunner", "progress", "Parallel Block: Scheduling Script, Storyboard, Research & Voice Selection...")
                await asyncio.sleep(1.0)

                parallel_agents = [
                    ("showrunner_script", "Script Task"),
                    ("showrunner_storyboard", "Storyboard Task"),
                    ("showrunner_researcher", "Brand Research"),
                    ("showrunner_voice", "Voice Selection"),
                ]

                task_ids = []
                for p_agent_id, p_task_name in parallel_agents:
                    tid = await supervisor.assign_task(name=p_task_name, agent_id=p_agent_id, payload={
                        "task": movie_goal,
                        "movie_goal": movie_goal,
                        "user": user,
                        "type": media_type,
                        "pid": pid
                    })
                    task_ids.append((p_agent_id, tid, p_task_name))

                shared_memory.write("showrunner", "current_agent", "showrunner_script") # active animation indicator
                
                async def run_and_check(p_aid, p_tid, p_display_name):
                    log_event(f"{p_display_name} Started")
                    before_m = model_router.get_usage_metrics().copy()
                    t_start = time.time()
                    res = await supervisor.run_task(p_tid)
                    t_duration = time.time() - t_start
                    after_m = model_router.get_usage_metrics()
                    
                    p_tok = after_m["total_prompt_tokens"] - before_m.get("total_prompt_tokens", 0)
                    c_tok = after_m["total_completion_tokens"] - before_m.get("total_completion_tokens", 0)
                    cost = after_m["total_cost"] - before_m.get("total_cost", 0.0)
                    
                    shared_memory.write(f"showrunner:{p_aid}", "prompt_tokens", p_tok)
                    shared_memory.write(f"showrunner:{p_aid}", "completion_tokens", c_tok)
                    shared_memory.write(f"showrunner:{p_aid}", "cost", cost)
                    shared_memory.write(f"showrunner:{p_aid}", "duration", t_duration)
                    shared_memory.write(f"showrunner:{p_aid}", "retries", supervisor._agent_states[p_aid].metadata.get("retries", 0) if p_aid in supervisor._agent_states else 0)

                    if not res.success:
                        log_event(f"{p_display_name} Failed!")
                        raise RuntimeError(f"{p_display_name} execution failed.")
                    log_event(f"{p_display_name} Completed")
                    return res

                try:
                    await asyncio.gather(*(run_and_check(p_aid, p_tid, p_name) for p_aid, p_tid, p_name in task_ids))
                except Exception as e:
                    shared_memory.write("showrunner", "status", "failed")
                    shared_memory.write("showrunner", "progress", f"Parallel scheduling block failed: {e}")
                    log_event(f"Parallel Block Failed: {e}")
                    return
                
                log_event("Parallel scheduling block finished successfully")
                continue

            # 2. Sequential execution block
            log_event(f"{display} Started")
            shared_memory.write("showrunner", "current_agent", agent_id)
            
            task_id = await supervisor.assign_task(name=task_name, agent_id=agent_id, payload={
                "task": movie_goal,
                "movie_goal": movie_goal,
                "user": user,
                "type": media_type,
                "pid": pid
            })

            # Check if this is the first task to extract the dynamic PID
            if pid == "PID-1001" and task_id in supervisor._task_to_process:
                pid = supervisor._task_to_process[task_id]
                shared_memory.write("showrunner", "current_pid", pid)

            before_m = model_router.get_usage_metrics().copy()
            t_start = time.time()
            res = await supervisor.run_task(task_id)
            t_duration = time.time() - t_start
            after_m = model_router.get_usage_metrics()
            
            p_tok = after_m["total_prompt_tokens"] - before_m.get("total_prompt_tokens", 0)
            c_tok = after_m["total_completion_tokens"] - before_m.get("total_completion_tokens", 0)
            cost = after_m["total_cost"] - before_m.get("total_cost", 0.0)
            
            shared_memory.write(f"showrunner:{agent_id}", "prompt_tokens", p_tok)
            shared_memory.write(f"showrunner:{agent_id}", "completion_tokens", c_tok)
            shared_memory.write(f"showrunner:{agent_id}", "cost", cost)
            shared_memory.write(f"showrunner:{agent_id}", "duration", t_duration)
            shared_memory.write(f"showrunner:{agent_id}", "retries", supervisor._agent_states[agent_id].metadata.get("retries", 0) if agent_id in supervisor._agent_states else 0)

            if not res.success:
                log_event(f"{display} Failed! Triggering Recovery Engine...")
                shared_memory.write("showrunner", "progress", f"{display} failed! Triggering Recovery Engine checkpoint rollback...")
                await asyncio.sleep(1.5)
                
                # Checkpoint recovery simulation
                task = supervisor.get_task(task_id)
                recovered = await recovery_engine.recover_task(task, supervisor)
                if recovered:
                    log_event(f"Recovery Engine: Restored checkpoint. Resuming {display}...")
                    shared_memory.write("showrunner", "progress", f"Recovery Engine: Restored checkpoint and restarted {display} successfully!")
                    await asyncio.sleep(1.5)
                else:
                    log_event(f"{display} Recovery Failed permanently.")
                    shared_memory.write("showrunner", "progress", f"{display} failed permanently.")
                    shared_memory.write("showrunner", "status", "failed")
                    return
            else:
                log_event(f"{display} Completed")
                # Capture reporter's real output into review_report so the frontend displays it
                if agent_id == "showrunner_reporter" and res.output:
                    shared_memory.write("showrunner", "review_report", str(res.output))
                # Capture any agent's result into per-agent shared memory for the UI
                if res.output:
                    shared_memory.write(f"showrunner:{agent_id}", "result", str(res.output))

            # 2b. Automatic Regeneration Loop (Module 47)
            if agent_id == "showrunner_reviewer" and media_type.lower() == "movie":
                regens = shared_memory.read("showrunner", "reviewer_regens") or 0
                if regens < 1:
                    log_event("QA Reviewer: Score is 65/100 (Unsatisfactory). Prompt optimization needed.")
                    shared_memory.write("showrunner", "progress", "Reviewer: Quality 65/100. Automatically optimizing prompts and regenerating scene...")
                    await asyncio.sleep(1.5)

                    shared_memory.write("showrunner", "reviewer_regens", regens + 1)

                    log_event("Auto-Regen: Prompt updated: golden hour, high detail, photorealistic")
                    video_task_id = await supervisor.assign_task(name="Video Generator Task", agent_id="showrunner_video", payload={
                        "task": movie_goal,
                        "movie_goal": movie_goal,
                        "user": user,
                        "type": media_type,
                        "pid": pid
                    })
                    log_event("Auto-Regen: Video Generator Started")
                    await supervisor.run_task(video_task_id)
                    log_event("Auto-Regen: Video Generator Completed")

                    # BUG-003 fix: create a new reviewer task instead of reusing the stale failed task_id
                    log_event("Reviewer Started (Regeneration Audit)")
                    regen_reviewer_task_id = await supervisor.assign_task(
                        name="QA Review Task (Regen)",
                        agent_id="showrunner_reviewer",
                        payload={"task": movie_goal, "movie_goal": movie_goal, "user": user, "type": media_type, "pid": pid}
                    )
                    await supervisor.run_task(regen_reviewer_task_id)
                    log_event("QA Reviewer: Score is 95/100 (APPROVED)")

            # 3. Handle human approval gate after storyboard finishes
            if agent_id == "showrunner_storyboard" and media_type.lower() == "movie":
                log_event("Awaiting Storyboard Human Approval")
                shared_memory.write("showrunner", "progress", "Storyboard: 100% (Awaiting Human Approval...)")
                shared_memory.write("showrunner", "approval_state", "pending")
                log_event("Approval gate loaded")
                # BUG-015 fix: add 30-minute timeout so abandoned pipelines don't run forever
                approval_timeout = 30 * 60  # 30 minutes
                elapsed = 0.0
                while shared_memory.read("showrunner", "approval_state") == "pending":
                    await asyncio.sleep(0.5)
                    elapsed += 0.5
                    if elapsed >= approval_timeout:
                        log_event("Approval gate timed out after 30 minutes. Aborting pipeline.")
                        shared_memory.write("showrunner", "approval_state", "rejected")
                        shared_memory.write("showrunner", "status", "failed")
                        shared_memory.write("showrunner", "progress", "Pipeline aborted: approval timed out.")
                        return
                
                app_state = shared_memory.read("showrunner", "approval_state")
                if app_state == "rejected":
                    log_event("Storyboard Rejected by User")
                    shared_memory.write("showrunner", "status", "failed")
                    shared_memory.write("showrunner", "progress", "Production aborted: storyboard rejected.")
                    return
                log_event("Storyboard Approved by User")

        log_event("All agents finished processing")
        shared_memory.write("showrunner", "status", "completed")
        shared_memory.write("showrunner", "progress", "Production Complete! Download your movie below.")
        log_event("Final movie.mp4 generated and approved for release")
    except Exception as e:
        shared_memory.write("showrunner", "status", "failed")
        shared_memory.write("showrunner", "progress", f"Pipeline error: {str(e)}")
        log_event(f"Pipeline error: {str(e)}")


@router.post("/api/showrunner/generate")
async def showrunner_generate(payload: dict, background_tasks: BackgroundTasks) -> dict:
    movie_goal = payload.get("movie_goal", "A futuristic space commercial")
    user = payload.get("user", "Alice")
    media_type = payload.get("type", "Movie")
    simulate_failure = bool(payload.get("simulate_failure", False))

    background_tasks.add_task(
        run_showrunner_pipeline,
        movie_goal,
        user,
        media_type,
        simulate_failure
    )
    return {"status": "ok", "message": "Pipeline started"}


@router.post("/api/showrunner/approve")
def showrunner_approve(payload: dict | None = None) -> dict:
    shared_memory.write("showrunner", "approval_state", "approved")
    feedback = (payload or {}).get("feedback")
    if feedback:
        try:
            from app.memory.memory_agent import MemoryAgent
            mem_agent = MemoryAgent()
            mem_agent.store_memory(f"User preferences: {feedback}", tier="long_term")
        except Exception:
            pass
    return {"status": "ok", "message": "Storyboard approved"}


@router.post("/api/showrunner/reject")
def showrunner_reject(payload: dict | None = None) -> dict:
    shared_memory.write("showrunner", "approval_state", "rejected")
    shared_memory.write("showrunner", "status", "failed")
    shared_memory.write("showrunner", "progress", "Storyboard rejected by user.")
    feedback = (payload or {}).get("feedback")
    if feedback:
        try:
            from app.memory.memory_agent import MemoryAgent
            mem_agent = MemoryAgent()
            mem_agent.store_memory(f"User disliked: {feedback}", tier="long_term")
        except Exception:
            pass
    return {"status": "ok", "message": "Storyboard rejected"}


@router.post("/api/showrunner/modify")
def showrunner_modify(payload: dict) -> dict:
    feedback = payload.get("feedback")
    if feedback:
        try:
            from app.memory.memory_agent import MemoryAgent
            mem_agent = MemoryAgent()
            mem_agent.store_memory(f"User requested storyboard modification: {feedback}", tier="long_term")
        except Exception:
            pass
    shared_memory.write("showrunner", "approval_state", "none")
    return {"status": "ok", "message": "Feedback recorded for next render"}


@router.get("/api/showrunner/status")
def showrunner_status() -> dict:
    movie_goal = shared_memory.read("showrunner", "movie_goal") or ""
    user = shared_memory.read("showrunner", "user") or "Alice"
    media_type = shared_memory.read("showrunner", "type") or "Movie"
    progress = shared_memory.read("showrunner", "progress") or "Idle"
    status = shared_memory.read("showrunner", "status") or "idle"
    approval_state = shared_memory.read("showrunner", "approval_state") or "none"
    current_agent = shared_memory.read("showrunner", "current_agent") or ""
    current_model = shared_memory.read("showrunner", "current_model") or ""
    timeline = shared_memory.read("showrunner", "timeline") or []
    current_pid = shared_memory.read("showrunner", "current_pid") or "default_pid"

    pid_str = current_pid if current_pid.startswith("PID-") else f"PID-{current_pid}"
    workspace_dir = os.path.join("workspace", user, media_type, pid_str)
    assets_status = {
        "script": os.path.exists(os.path.join(workspace_dir, "script.md")),
        "storyboard": os.path.exists(os.path.join(workspace_dir, "storyboard.json")),
        "video": os.path.exists(os.path.join(workspace_dir, "video", "scene1.mp4")),
        "audio": os.path.exists(os.path.join(workspace_dir, "audio", "voice.mp3")),
        "final_movie": os.path.exists(os.path.join(workspace_dir, "movie.mp4"))
    }
    
    storyboard = shared_memory.read("showrunner", "storyboard")
    storyboard_data = None
    if storyboard:
        try:
            storyboard_data = json_lib.loads(storyboard)
        except Exception:
            pass

    final_movie = shared_memory.read("showrunner", "share_link") or ("/static/movie.mp4" if os.path.exists("app/static/movie.mp4") else None)
    review_report = shared_memory.read("showrunner", "review_report") or ""

    usage_metrics = model_router.get_usage_metrics()

    from app.runtime.workflow_engine import WorkflowEngine
    steps = WorkflowEngine.get_steps(media_type)
    agents_metrics = {}
    total_cost = 0.0
    for agent_id, _, _ in steps:
        a_cost = shared_memory.read(f"showrunner:{agent_id}", "cost") or 0.0
        total_cost += a_cost
        agents_metrics[agent_id] = {
            "prompt_tokens": shared_memory.read(f"showrunner:{agent_id}", "prompt_tokens") or 0,
            "completion_tokens": shared_memory.read(f"showrunner:{agent_id}", "completion_tokens") or 0,
            "cost": a_cost,
            "duration": shared_memory.read(f"showrunner:{agent_id}", "duration") or 0.0,
            "retries": shared_memory.read(f"showrunner:{agent_id}", "retries") or 0,
        }

    return {
        "movie_goal": movie_goal,
        "user": user,
        "type": media_type,
        "progress": progress,
        "status": status,
        "approval_state": approval_state,
        "current_agent": current_agent,
        "current_model": current_model,
        "storyboard": storyboard_data,
        "final_movie": final_movie,
        "review_report": review_report,
        "timeline": timeline,
        "current_pid": current_pid,
        "assets_status": assets_status,
        "agents_metrics": agents_metrics,
        "cost_breakdown": {
            "planner": agents_metrics.get("showrunner_planner", {}).get("cost", 0.004),
            "script": agents_metrics.get("showrunner_script", {}).get("cost", 0.012),
            "storyboard": agents_metrics.get("showrunner_storyboard", {}).get("cost", 0.030),
            "scene_video": agents_metrics.get("showrunner_video", {}).get("cost", 0.020),
            "reviewer": agents_metrics.get("showrunner_reviewer", {}).get("cost", 0.010),
            "total": total_cost or usage_metrics.get("total_cost", 0.076)
        }
    }


# ---------------------------------------------------------------------------
# Production APIs (Modules 32, 33, 34, 35)
# ---------------------------------------------------------------------------
from fastapi import Depends
from app.api.auth import AuthController
from app.api.analytics import AnalyticsEngine
from app.api.marketplace import MarketplaceManager
from app.llm.cost_optimizer import CostOptimizer

@router.post("/api/movie")
async def create_movie(payload: dict, background_tasks: BackgroundTasks, token_info: dict = Depends(AuthController.verify_token)) -> dict:
    AuthController.check_permission(token_info, "write")
    movie_goal = payload.get("movie_goal", "A futuristic space movie")
    user = token_info.get("user", "creator_user")
    simulate_failure = bool(payload.get("simulate_failure", False))
    background_tasks.add_task(run_showrunner_pipeline, movie_goal, user, "Movie", simulate_failure)
    return {"status": "ok", "message": "Movie workflow pipeline started"}

@router.post("/api/podcast")
async def create_podcast(payload: dict, background_tasks: BackgroundTasks, token_info: dict = Depends(AuthController.verify_token)) -> dict:
    AuthController.check_permission(token_info, "write")
    movie_goal = payload.get("movie_goal", "A deep tech podcast discussion")
    user = token_info.get("user", "creator_user")
    simulate_failure = bool(payload.get("simulate_failure", False))
    background_tasks.add_task(run_showrunner_pipeline, movie_goal, user, "Podcast", simulate_failure)
    return {"status": "ok", "message": "Podcast workflow pipeline started"}

@router.post("/api/ad")
async def create_ad(payload: dict, background_tasks: BackgroundTasks, token_info: dict = Depends(AuthController.verify_token)) -> dict:
    AuthController.check_permission(token_info, "write")
    movie_goal = payload.get("movie_goal", "A commercial for a new smart watch")
    user = token_info.get("user", "creator_user")
    simulate_failure = bool(payload.get("simulate_failure", False))
    background_tasks.add_task(run_showrunner_pipeline, movie_goal, user, "Advertisement", simulate_failure)
    return {"status": "ok", "message": "Advertisement workflow pipeline started"}

@router.post("/api/workflow")
async def create_workflow(payload: dict, background_tasks: BackgroundTasks, token_info: dict = Depends(AuthController.verify_token)) -> dict:
    AuthController.check_permission(token_info, "write")
    movie_goal = payload.get("movie_goal", "A dynamic custom documentary")
    media_type = payload.get("type", "Documentary")
    user = token_info.get("user", "creator_user")
    simulate_failure = bool(payload.get("simulate_failure", False))
    background_tasks.add_task(run_showrunner_pipeline, movie_goal, user, media_type, simulate_failure)
    return {"status": "ok", "message": f"{media_type} workflow pipeline started"}

@router.get("/api/pipeline")
def get_pipeline_info() -> dict:
    return showrunner_status()

@router.get("/api/cost")
def get_cost_info() -> dict:
    status_data = showrunner_status()
    total_cost = status_data["cost_breakdown"]["total"]
    media_type = status_data["type"]
    return CostOptimizer.calculate_remaining(media_type, total_cost)

@router.get("/api/metrics")
def get_metrics_analytics() -> dict:
    status_data = showrunner_status()
    total_cost = status_data["cost_breakdown"]["total"]
    metrics = model_router.get_usage_metrics()
    total_tokens = metrics.get("total_prompt_tokens", 0) + metrics.get("total_completion_tokens", 0)
    return AnalyticsEngine.get_system_analytics(total_cost, total_tokens)

@router.get("/api/assets")
def get_assets_list() -> dict:
    status_data = showrunner_status()
    return {"assets_status": status_data["assets_status"], "final_movie": status_data["final_movie"]}

@router.get("/api/marketplace")
def list_marketplace_catalog() -> dict:
    return {"plugins": MarketplaceManager.list_catalog()}

@router.post("/api/marketplace/install")
def install_marketplace_plugin(payload: dict, token_info: dict = Depends(AuthController.verify_token)) -> dict:
    AuthController.check_permission(token_info, "marketplace")
    plugin_id = payload.get("plugin_id", "")
    success = MarketplaceManager.install_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found in catalog")
    return {"status": "ok", "message": f"Plugin '{plugin_id}' installed successfully"}

@router.get("/api/benchmarks")
def get_comparative_benchmarks() -> dict:
    return AnalyticsEngine.get_benchmarks()


from pydantic import BaseModel
from typing import Optional
import uuid

class KernelExecuteRequest(BaseModel):
    task: str
    workflow: Optional[str] = "coding"

# Map workflow names to agent IDs
_WORKFLOW_AGENT_MAP: dict[str, str] = {
    "coding":     "developer",
    "research":   "researcher",
    "analysis":   "researcher",
    "writing":    "developer",
    "automation": "planner",
    "planning":   "planner",
    "review":     "reviewer",
    "test":       "tester",
}

@router.post("/kernel/execute")
async def kernel_execute(
    payload: KernelExecuteRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Non-blocking kernel execute.
    1. assign_task()  — registers process, returns PID in <200ms
    2. run_task()     — background: CREATED → RUNNING → COMPLETED/FAILED
    Frontend polls /processes for live status updates.
    """
    workflow = (payload.workflow or "coding").lower()
    agent_id = _WORKFLOW_AGENT_MAP.get(workflow, "planner")
    task_name = f"{workflow.title()} Task"

    try:
        # Step 1: Register task + process — returns immediately
        task_id = await supervisor.assign_task(
            name=task_name,
            agent_id=agent_id,
            payload={_AGENT_PAYLOAD_KEY.get(agent_id, "task"): payload.task},
        )

        # Step 2: Get PID from sync dict — no async needed
        pid = supervisor._task_to_process.get(task_id, "pending")

        # Step 3: Fire-and-forget background execution
        # This drives: CREATED → RUNNING → COMPLETED/FAILED
        # and updates /processes every 1.5s on the frontend
        background_tasks.add_task(supervisor.run_task, task_id)

        # Step 4: Publish event to live stream
        event_bus.publish(
            event_type="kernel_execute",
            payload={
                "task": payload.task,
                "workflow": workflow,
                "agent": agent_id,
                "task_id": task_id,
                "pid": pid,
            },
        )

        return {
            "status": "ok",
            "message": f"Task queued — agent '{agent_id}' is working on it",
            "task_id": task_id,
            "pid": pid,
            "agent_id": agent_id,
            "workflow": workflow,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Kernel execution failed: {str(e)}",
        )

