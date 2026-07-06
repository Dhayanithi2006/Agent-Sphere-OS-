"""FastAPI routes for AgentSphere OS runtime interaction."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.developer import DeveloperAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.supervisor.supervisor import Supervisor

router = APIRouter()
supervisor = Supervisor()

for agent in (PlannerAgent(), ResearcherAgent(), DeveloperAgent(), TesterAgent(), ReviewerAgent()):
    supervisor.register_agent(agent)


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
