"""Pydantic models for memory layer."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional


class EpisodicEntry(BaseModel):
    session_id: str
    turn: int
    user_input: str
    tool_used: Optional[str] = None
    tool_result: Any = None
    match_type: str = ""
    similarity_score: float = 0.0
    runtime_ms: int = 0
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkingMemory(BaseModel):
    session_id: str
    intent: str
    entities: dict = {}
    subtasks: list[str] = []
    active_tool: Optional[str] = None
    intermediate_results: list[Any] = []
