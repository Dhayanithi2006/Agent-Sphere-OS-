"""REST API endpoints for process lifecycle management in the microkernel."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.models.process import ProcessStatus
from app.runtime.process_manager import ProcessManager

router = APIRouter(prefix="/kernel/processes", tags=["processes"])


class CreateProcessRequest(BaseModel):
    """Payload schema for process creation API."""
    name: str = Field(..., description="The name identifying the process (e.g. agent name)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata to attach to process context")


class ProcessResponse(BaseModel):
    """Schema representing serializable process state."""
    process_id: str = Field(..., description="Unique generated process identification string")
    name: str = Field(..., description="Process name")
    status: str = Field(..., description="Lifecycle status enum value")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags")


def get_process_manager(request: Request) -> ProcessManager:
    """Dependency provider retrieving the process manager from FastAPI app state."""
    return request.app.state.process_manager


@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(
    payload: CreateProcessRequest,
    pm: ProcessManager = Depends(get_process_manager)
) -> Dict[str, Any]:
    """Create a new process and allocate a unique PID."""
    proc = await pm.create_process(payload.name, payload.metadata)
    return {
        "process_id": proc.process_id,
        "name": proc.name,
        "status": proc.status.value,
        "created_at": proc.created_at.isoformat(),
        "updated_at": proc.updated_at.isoformat(),
        "metadata": proc.metadata,
    }


@router.get("", response_model=List[ProcessResponse])
async def list_processes(pm: ProcessManager = Depends(get_process_manager)) -> List[Dict[str, Any]]:
    """List all processes registered in the kernel."""
    processes = await pm.list_processes()
    return [
        {
            "process_id": proc.process_id,
            "name": proc.name,
            "status": proc.status.value,
            "created_at": proc.created_at.isoformat(),
            "updated_at": proc.updated_at.isoformat(),
            "metadata": proc.metadata,
        }
        for proc in processes
    ]


@router.get("/{pid}", response_model=ProcessResponse)
async def get_process(
    pid: str,
    pm: ProcessManager = Depends(get_process_manager)
) -> Dict[str, Any]:
    """Fetch status and details of a single process by PID."""
    proc = await pm.repository.get(pid)
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process with ID '{pid}' does not exist"
        )
    return {
        "process_id": proc.process_id,
        "name": proc.name,
        "status": proc.status.value,
        "created_at": proc.created_at.isoformat(),
        "updated_at": proc.updated_at.isoformat(),
        "metadata": proc.metadata,
    }


@router.post("/{pid}/suspend")
async def suspend_process(
    pid: str,
    pm: ProcessManager = Depends(get_process_manager)
) -> Dict[str, str]:
    """Suspend a running or created process."""
    success = await pm.suspend_process(pid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to suspend process '{pid}'. Ensure it exists and is running/created."
        )
    return {"status": "ok", "message": f"Process '{pid}' has been suspended"}


@router.post("/{pid}/resume")
async def resume_process(
    pid: str,
    pm: ProcessManager = Depends(get_process_manager)
) -> Dict[str, str]:
    """Resume a suspended process."""
    success = await pm.resume_process(pid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resume process '{pid}'. Ensure it exists and is suspended."
        )
    return {"status": "ok", "message": f"Process '{pid}' has been resumed"}


@router.post("/{pid}/kill")
async def kill_process(
    pid: str,
    pm: ProcessManager = Depends(get_process_manager)
) -> Dict[str, str]:
    """Terminate/kill a process."""
    success = await pm.kill_process(pid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to kill process '{pid}'. Ensure it exists and is not already terminal."
        )
    return {"status": "ok", "message": f"Process '{pid}' has been killed"}


@router.post("/{pid}/restart")
async def restart_process(pid: str) -> Dict[str, str]:
    """Restart a process by spawning a new one with matching configuration."""
    try:
        from app.core.shared import kernel
        new_pid = await kernel.restart_agent_process(pid)
        return {"status": "ok", "message": f"Process '{pid}' has been restarted as '{new_pid}'", "new_pid": new_pid}
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to restart process '{pid}': {e}"
        )

