"""FastAPI router for real-time monitoring and analytics dashboard metrics."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.core.config import settings
from app.memory.shared_memory import SharedMemory
from app.core.shared import (
    resource_manager,
    dependency_manager,
    execution_engine,
    model_router,
    checkpoint_manager,
    event_bus,
    supervisor,
    scheduler,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
shared_memory = SharedMemory()


@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Retrieve current system CPU, RAM, and Disk metrics along with supervisor stats."""
    sys_metrics = resource_manager.get_system_metrics()

    # Fetch task status statistics
    supervisor_status = await supervisor.get_supervisor_status()
    tasks = supervisor_status.get("tasks", [])

    total_tasks = len(tasks)
    running_tasks = sum(1 for t in tasks if t.get("status") == "running")
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    failed_tasks = sum(1 for t in tasks if t.get("status") == "failed")

    # Process manager tracking
    process_table = await supervisor.list_processes()
    total_processes = len(process_table)
    suspended_processes = sum(1 for p in process_table if p.get("status") == "SUSPENDED")
    active_processes = sum(1 for p in process_table if p.get("status") == "RUNNING")

    return {
        "system": sys_metrics,
        "tasks": {
            "total": total_tasks,
            "running": running_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
        },
        "processes": {
            "total": total_processes,
            "active": active_processes,
            "suspended": suspended_processes,
        },
    }


@router.get("/dependency-graph")
def get_dependency_graph() -> Dict[str, Any]:
    """Retrieve the nodes, edges, cycle status, and topological ordering of the dependency graph."""
    nodes = [{"id": node, "label": node} for node in dependency_manager.get_nodes()]
    edges = [{"from": src, "to": dest} for src, dest in dependency_manager.get_edges()]

    has_cycle = dependency_manager.has_cycle()
    try:
        topo_order = dependency_manager.topological_sort()
    except Exception:
        topo_order = []

    return {
        "nodes": nodes,
        "edges": edges,
        "has_cycle": has_cycle,
        "topological_order": topo_order,
    }


@router.post("/dependency")
def add_dependency(payload: Dict[str, str]) -> Dict[str, str]:
    """Manually add a dependency link."""
    source = payload.get("source")
    target = payload.get("target")
    if not source or not target:
        raise HTTPException(status_code=400, detail="Source and target nodes are required.")
    dependency_manager.add_dependency(source, target)
    return {"status": "ok", "message": f"Added dependency: {source} -> {target}"}


@router.delete("/dependency")
def remove_dependency(source: str, target: str) -> Dict[str, str]:
    """Manually remove a dependency link."""
    dependency_manager.remove_dependency(source, target)
    return {"status": "ok", "message": f"Removed dependency: {source} -> {target}"}


@router.get("/memory")
def get_memory_snapshot() -> Dict[str, Any]:
    """Retrieve shared memory key-value entries."""
    return shared_memory.snapshot()


@router.post("/processes/{pid}/suspend")
async def suspend_process(pid: str) -> Dict[str, str]:
    """Suspend an active process."""
    success = await supervisor.process_manager.suspend_process(pid)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to suspend process.")
    return {"status": "ok"}


@router.post("/processes/{pid}/resume")
async def resume_process(pid: str) -> Dict[str, str]:
    """Resume a suspended process."""
    success = await supervisor.process_manager.resume_process(pid)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume process.")
    return {"status": "ok"}


@router.post("/processes/{pid}/kill")
async def kill_process(pid: str) -> Dict[str, str]:
    """Kill an active process."""
    success = await supervisor.process_manager.kill_process(pid)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to kill process.")
    return {"status": "ok"}


@router.get("/settings")
def get_dashboard_settings() -> Dict[str, Any]:
    """Retrieve dashboard settings configuration parameters."""
    return {
        "qwen_api_key": settings.qwen_api_key or "",
        "qwen_base_url": settings.qwen_base_url or "",
        "qwen_model": settings.qwen_model or "",
        "max_workers": execution_engine._max_workers or 4,
    }


@router.post("/settings")
def update_dashboard_settings(payload: Dict[str, Any]) -> Dict[str, str]:
    """Update settings configurations dynamically and propagate client reinstantiations."""
    if "qwen_api_key" in payload:
        settings.qwen_api_key = payload["qwen_api_key"]
    if "qwen_base_url" in payload:
        settings.qwen_base_url = payload["qwen_base_url"]
    if "qwen_model" in payload:
        settings.qwen_model = payload["qwen_model"]
    if "max_workers" in payload:
        limit = int(payload["max_workers"])
        execution_engine.set_concurrency_limit(limit)
        scheduler.max_concurrency = limit
        scheduler._semaphore = asyncio.Semaphore(limit)

    # Recreate LLM Client & Providers
    from app.llm.qwen_client import QwenClient
    from app.llm.qwen_provider import QwenProvider

    new_client = QwenClient()
    model_router.client = new_client
    model_router.register_provider("qwen", QwenProvider(
        base_url=settings.qwen_base_url,
        api_key=settings.qwen_api_key,
        model=settings.qwen_model
    ))

    # Propagate client references back to supervisor agents
    for agent in supervisor._agents.values():
        if hasattr(agent, "client"):
            agent.client = new_client

    # Write updates to .env file
    env_lines = [
        f"QWEN_API_KEY={settings.qwen_api_key or ''}",
        f"QWEN_BASE_URL={settings.qwen_base_url or ''}",
        f"QWEN_MODEL={settings.qwen_model or ''}",
    ]
    with open(".env", "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines) + "\n")

    return {"status": "ok", "message": "Settings updated and persisted."}


@router.get("/executions")
def get_execution_metrics() -> Dict[str, Any]:
    """Retrieve execution metrics and historic run data from the execution engine."""
    metrics = execution_engine.get_metrics()
    history = execution_engine.get_execution_history()
    return {
        "metrics": metrics,
        "history": history,
    }


@router.get("/token-cost")
def get_token_cost_metrics() -> Dict[str, Any]:
    """Retrieve OpenAI compatible API usage, token counts, and cost details from the router."""
    return model_router.get_usage_metrics()


@router.get("/checkpoints")
def list_checkpoints() -> List[Dict[str, Any]]:
    """Retrieve all saved checkpoints along with metadata and state sizes."""
    checkpoints = checkpoint_manager.list_checkpoints()
    return [
        {
            "id": cp.id,
            "task_id": cp.task_id,
            "name": cp.name,
            "timestamp": cp.created_at.isoformat(),
            "state_size_bytes": len(str(cp.state)),
        }
        for cp in checkpoints
    ]


@router.websocket("/ws")
async def websocket_dashboard(websocket: WebSocket) -> None:
    """Realtime WebSocket endpoint streaming metrics, processes, costs, and event feeds."""
    await websocket.accept()
    event_bus.register_websocket(websocket)
    try:
        while True:
            # Gather fresh metrics and stats
            sys_metrics = resource_manager.get_system_metrics()
            process_table = await supervisor.list_processes()
            usage_metrics = model_router.get_usage_metrics()
            recent_events = event_bus.get_recent_events(limit=10)
            mem_snapshot = shared_memory.snapshot()

            payload = {
                "type": "dashboard_update",
                "system": sys_metrics,
                "processes": process_table,
                "llm_usage": usage_metrics,
                "events": recent_events,
                "memory_snapshot": mem_snapshot,
                "memory_keys": list(mem_snapshot.keys()),
            }

            lock = event_bus._ws_locks.get(websocket)
            if lock:
                async with lock:
                    await websocket.send_json(payload)
            else:
                await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unregister_websocket(websocket)
