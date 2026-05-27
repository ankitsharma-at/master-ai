"""Health check endpoints."""
from fastapi import APIRouter
from registry.db import ToolRegistryDB

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Check API health."""
    return {"status": "ok"}


@router.get("/registry")
async def registry_health():
    """Check registry health."""
    db = ToolRegistryDB()
    tools = await db.list()
    return {"status": "ok", "tools_count": len(tools)}
