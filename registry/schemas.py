"""Pydantic models for Tool registry records."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ToolRecord(BaseModel):
    id: str
    name: str
    description: str
    category: str
    language: str
    version: str = "1.0.0"
    code_path: str
    dependencies: list[str] = []
    input_schema: dict = {}
    output_schema: dict = {}
    reliability_score: int = 0
    use_count: int = 0
    success_count: int = 0
    status: str = "active"
    tags: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ToolSearchResult(BaseModel):
    tool: ToolRecord
    similarity_score: float
    match_type: str


class CriticResult(BaseModel):
    passed: bool
    reliability_score: int = 0
    issues: list[dict] = []
    summary: str = ""
