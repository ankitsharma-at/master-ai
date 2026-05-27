"""POST /task endpoint."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.orchestrator import Orchestrator

router = APIRouter(prefix="/task", tags=["tasks"])


class TaskRequest(BaseModel):
    command: str
    session_id: Optional[str] = None


_orchestrator = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@router.post("/")
async def run_task(req: TaskRequest, orch: Orchestrator = Depends(get_orchestrator)):
    """Execute a command."""
    result = await orch.run(req.command, session_id=req.session_id)
    if not result.get("success") and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
