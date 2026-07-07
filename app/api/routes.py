"""FastAPI routes for AgentSphere OS runtime interaction."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.developer import DeveloperAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.dependency.dependency_manager import DependencyManager
from app.memory.shared_memory import SharedMemory
from app.supervisor.supervisor import Supervisor

router = APIRouter()
supervisor = Supervisor()
shared_memory = SharedMemory()
dependency_manager = DependencyManager()

for agent in (PlannerAgent(), ResearcherAgent(), DeveloperAgent(), TesterAgent(), ReviewerAgent()):
    supervisor.register_agent(agent)

# Seed a simple dependency chain so the dependency APIs expose meaningful data.
dependency_manager.add_dependency("planner", "researcher")
dependency_manager.add_dependency("researcher", "developer")
dependency_manager.add_dependency("developer", "tester")
dependency_manager.add_dependency("tester", "reviewer")


@router.get("/")
def root() -> dict[str, str]:
    """Return a simple landing response for the service."""
    return {"message": "AgentSphere OS is running"}


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple health indicator for the service."""
    return {"status": "ok"}


@router.post("/tasks")
def submit_task(name: str, agent_id: str, payload: dict | None = None) -> dict[str, str]:
    """Submit a task to the supervisor for execution."""
    task_id = supervisor.submit_task(name=name, agent_id=agent_id, payload=payload)
    return {"task_id": task_id}


@router.post("/assign")
def assign_task(payload: dict[str, object]) -> dict[str, str]:
    """Assign a task using the supervisor process table."""
    agent_id = str(payload.get("agent_id") or payload.get("agent") or "")
    task_name = str(payload.get("name") or payload.get("task") or "")
    task_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else None
    if task_payload is None and payload.get("task") is not None:
        task_payload = {"task": str(payload.get("task", ""))}

    task_id = supervisor.assign_task(
        name=task_name,
        agent_id=agent_id,
        payload=task_payload,
    )
    supervisor.run_task(task_id)
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    """Retrieve the status and result of a task."""
    task = supervisor.get_task(task_id)
    return {"task_id": task.task_id, "status": task.status.value, "result": task.result, "error": task.error}


@router.post("/tasks/{task_id}/run")
def run_task(task_id: str) -> dict[str, object]:
    """Execute a previously submitted task."""
    try:
        result = supervisor.run_task(task_id)
    except KeyError as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": result.success, "output": result.output, "error": result.error}


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
        "checkpoint_manager": False,
        "recovery_engine": False,
    }


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


@router.get("/dependencies")
def get_dependencies() -> dict[str, list[str]]:
    """Return the dependency graph as a serializable mapping of prerequisites."""
    return {agent: sorted(dependency_manager.get_dependents(agent)) for agent in dependency_manager.get_nodes()}
