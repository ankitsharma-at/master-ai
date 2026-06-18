"""Supabase-backed episodic memory for session history."""

from datetime import datetime
from typing import Optional, List, Any

import structlog
from supabase import create_client

from memory.schemas import EpisodicEntry
from core.config import get_settings

log = structlog.get_logger()


class EpisodicMemory:
    def __init__(self):
        settings = get_settings()

        self.supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

    async def create_session(self, session_id: str):
        """Create a session if it doesn't already exist."""

        self.supabase.table("sessions").upsert(
            {"id": session_id}
        ).execute()

        log.debug("episodic.session_created", session=session_id)

    async def store(
        self,
        session_id: str,
        user_input: str,
        tool_id: Optional[str] = None,
        execution_mode: str = "direct_llm",
        tool_result: Any = None,
        match_type: str = "",
        similarity_score: float = 0.0,
        runtime_ms: int = 0,
        success: bool = True,
    ):
        """Store a single turn in episodic memory."""

        response = (
            self.supabase.table("tool_usage")
            .select("*", count="exact")
            .eq("session_id", session_id)
            .execute()
        )

        turn = response.count if hasattr(response, "count") else 0

        entry_data = {
            "session_id": session_id,
            # "turn": turn,  # Remove if this column doesn't exist
            "tool_id": tool_id,
            "execution_mode": execution_mode,
            "user_input": user_input,
            "tool_result": tool_result,
            "match_type": match_type,
            "similarity_score": similarity_score,
            "runtime_ms": runtime_ms,
            "success": success,
        }

        self.supabase.table("tool_usage").insert(
            entry_data
        ).execute()

        log.debug(
            "episodic.store",
            session=session_id,
            
        )

    async def get_session_history(
        self,
        session_id: str,
    ) -> List[EpisodicEntry]:
        """Retrieve all entries for a session."""

        response = (
            self.supabase.table("tool_usage")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )

        entries = []

        for idx, row in enumerate(response.data):
            entry = EpisodicEntry(
                session_id=session_id,
                turn=idx,
                user_input=row.get("user_input", ""),
                tool_used=row.get("tool_id"),  # fixed
                tool_result=row.get("tool_result"),
                match_type=row.get("match_type", ""),
                similarity_score=row.get(
                    "similarity_score", 0.0
                ),
                runtime_ms=row.get("runtime_ms", 0),
                success=row.get("success", True),
                timestamp=(
                    datetime.fromisoformat(
                        row["created_at"]
                    )
                    if row.get("created_at")
                    else datetime.utcnow()
                ),
            )

            entries.append(entry)

        return entries