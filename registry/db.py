"""Supabase CRUD operations for tool registry."""
import uuid
from datetime import datetime
from typing import Optional, List
import structlog
from registry.schemas import ToolRecord
from core.config import get_settings
from supabase import create_client, Client

log = structlog.get_logger()


class ToolRegistryDB:
    def __init__(self):
        settings = get_settings()
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

    async def create(self, tool_meta: dict, reliability_score: int = 0) -> ToolRecord:
        """Create a new tool record."""
        tool_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        settings = get_settings()

        tool_data = {
            "id": tool_id,
            "name": tool_meta.get("name", f"tool_{uuid.uuid4().hex[:8]}"),
            "description": tool_meta.get("description", ""),
            "category": tool_meta.get("category", "workflow"),
            "language": tool_meta.get("language", "python"),
            "version": tool_meta.get("version", "1.0.0"),
            "code_path": tool_meta.get("code_path", f"{settings.tools_dir}/{tool_id}.py"),
            "dependencies": tool_meta.get("dependencies", []),
            "input_schema": tool_meta.get("input_schema", {}),
            "output_schema": tool_meta.get("output_schema", {}),
            "reliability_score": reliability_score,
            "status": "active",
            "tags": tool_meta.get("tags", []),
        }

        response = self.supabase.table("tools").insert(tool_data).execute()

        if response.data:
            log.info("registry.tool_created", tool_id=tool_id)
            return self._row_to_record(response.data[0])

        return await self.get(tool_id)

    async def get(self, tool_id: str) -> Optional[ToolRecord]:
        response = (
        self.supabase
        .table("tools")
        .select("*")
        .eq("id", tool_id)
        .limit(1)
        .execute()
    )

        if not response.data:
             return None

        return self._row_to_record(response.data[0])

    async def get_by_name(self, name: str) -> Optional[ToolRecord]:
        response = (
            self.supabase
            .table("tools")
            .select("*")
            .eq("name", name)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return self._row_to_record(response.data[0])
        

    async def list(self, category: Optional[str] = None, status: str = "active") -> List[ToolRecord]:
        """List tools filtered by category and status."""
        query = self.supabase.table("tools").select("*").eq("status", status)
        if category:
            query = query.eq("category", category)
        response = query.order("updated_at", desc=True).execute()
        return [self._row_to_record(row) for row in response.data]

    async def increment_usage(self, tool_id: str, success: bool = True):
        """Increment usage statistics for a tool."""
        now = datetime.utcnow().isoformat()
        tool = await self.get(tool_id)
        if not tool:
            return

        update_data = {"use_count": tool.use_count + 1, "updated_at": now}
        if success:
            update_data["success_count"] = tool.success_count + 1

        self.supabase.table("tools").update(update_data).eq("id", tool_id).execute()

    async def deprecate(self, tool_id: str):
        """Mark a tool as deprecated."""
        now = datetime.utcnow().isoformat()
        self.supabase.table("tools").update({
            "status": "deprecated",
            "updated_at": now
        }).eq("id", tool_id).execute()

    def _row_to_record(self, row: dict) -> ToolRecord:
        """Convert database row to ToolRecord."""
        return ToolRecord(
            id=row.get("id"),
            name=row.get("name"),
            description=row.get("description"),
            category=row.get("category", "workflow"),
            language=row.get("language", "python"),
            version=row.get("version", "1.0.0"),
            code_path=row.get("code_path"),
            dependencies=row.get("dependencies", []) if isinstance(row.get("dependencies"), list) else [],
            input_schema=row.get("input_schema", {}),
            output_schema=row.get("output_schema", {}),
            reliability_score=row.get("reliability_score", 0),
            use_count=row.get("use_count", 0),
            success_count=row.get("success_count", 0),
            status=row.get("status", "active"),
            tags=row.get("tags", []) if isinstance(row.get("tags"), list) else [],
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.utcnow(),
        )
