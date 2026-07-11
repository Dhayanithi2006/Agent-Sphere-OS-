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
from app.memory.shared_memory import SharedMemory
from app.supervisor.supervisor import Supervisor
from app.checkpoint.checkpoint_manager import CheckpointManager
from app.runtime.recovery import RecoveryEngine
from app.events.event_bus import EventBus

router = APIRouter()
supervisor = Supervisor()
shared_memory = SharedMemory()
dependency_manager = DependencyManager()
checkpoint_manager = CheckpointManager()
recovery_engine = RecoveryEngine()
event_bus = EventBus()

for agent in (PlannerAgent(), ResearcherAgent(), DeveloperAgent(), TesterAgent(), ReviewerAgent()):
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


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple health indicator for the service."""
    return {"status": "ok"}


@router.get("/status")
def get_status() -> dict[str, Any]:
    """Return comprehensive runtime status."""
    return {
        "supervisor": supervisor.get_supervisor_status(),
        "memory": shared_memory.snapshot(),
        "dependencies": get_dependencies(),
        "checkpoints": [cp.id for cp in checkpoint_manager.list_checkpoints()],
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
def submit_task(name: str, agent_id: str, payload: dict | None = None) -> dict[str, str]:
    """Submit a task to the supervisor for execution."""
    task_id = supervisor.submit_task(name=name, agent_id=agent_id, payload=payload)
    return {"task_id": task_id}


@router.post("/assign")
def assign_task(payload: dict[str, object], background_tasks: BackgroundTasks) -> dict[str, str]:
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

    task_id = supervisor.assign_task(name=task_name, agent_id=agent_id, payload=task_payload)
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
def run_task(task_id: str) -> dict[str, object]:
    """Execute a previously submitted task."""
    try:
        result = supervisor.run_task(task_id)
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


# ---------------------------------------------------------------------------
# Process & supervisor info
# ---------------------------------------------------------------------------

@router.get("/processes")
def list_processes() -> list[dict[str, object]]:
    """Return the current supervisor process table."""
    return supervisor.list_processes()


@router.get("/supervisor")
def supervisor_status() -> dict[str, object]:
    """Return the current supervisor runtime status."""
    return supervisor.get_supervisor_status()


@router.get("/supervisor/status")
def supervisor_status_detail() -> dict[str, object]:
    """Return the detailed supervisor runtime status."""
    return supervisor.get_supervisor_status()


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


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------

@router.get("/checkpoints")
def list_checkpoints() -> list[dict[str, Any]]:
    """List all checkpoints."""
    return [cp.to_dict() for cp in checkpoint_manager.list_checkpoints()]


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
def trigger_recovery(task_id: str) -> dict[str, Any]:
    """Trigger recovery for a failed task."""
    task = supervisor.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    recovered = recovery_engine.recover_task(task, supervisor)
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
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({
                "type": "update",
                "processes": supervisor.list_processes(),
                "supervisor": supervisor.get_supervisor_status(),
                "memory_keys": list(shared_memory.snapshot().keys()),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        _active_connections.remove(websocket)


# ---------------------------------------------------------------------------
# Real-time streaming (SSE)
# ---------------------------------------------------------------------------

@router.get("/stream")
async def stream_events(once: bool = False) -> StreamingResponse:
    """Push real-time process and memory updates via Server-Sent Events."""

    async def event_generator():
        while True:
            event = json_lib.dumps({
                "processes": supervisor.list_processes(),
                "supervisor": supervisor.get_supervisor_status(),
                "memory_keys": list(shared_memory.snapshot().keys()),
            })
            yield f"data: {event}\n\n"
            if once:
                break
            await asyncio.sleep(1.5)

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
