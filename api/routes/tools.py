"""Tool registry endpoints."""
from fastapi import APIRouter, HTTPException
from registry.db import ToolRegistryDB

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/")
async def list_tools(category: str = None, status: str = "active"):
    """List all tools."""
    db = ToolRegistryDB()
    return await db.list(category=category, status=status)


@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """Get tool by name."""
    db = ToolRegistryDB()
    tool = await db.get_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.delete("/{tool_name}")
async def deprecate_tool(tool_name: str):
    """Deprecate a tool."""
    db = ToolRegistryDB()
    tool = await db.get_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    await db.deprecate(tool.id)
    return {"message": f"Tool '{tool_name}' deprecated"}
