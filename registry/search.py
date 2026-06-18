"""Semantic search using Supabase pgvector."""
import structlog
from typing import Optional
from registry.embedder import ToolEmbedder
from registry.db import ToolRegistryDB
from registry.schemas import ToolSearchResult
from core.config import get_settings
from supabase import create_client

log = structlog.get_logger()


class ToolSearcher:
    def __init__(self):
        settings = get_settings()
        self.embedder = ToolEmbedder()
        self.db = ToolRegistryDB()
        self.supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    async def find(self, query: str, top_k: int = 3) -> Optional[ToolSearchResult]:
        """Search for similar tools using semantic similarity."""
        embedding = self.embedder.embed(query)

        response = self.supabase.rpc(
            "search_tools",
            {"query_embedding": embedding, "match_count": top_k}
        ).execute()

        if not response.data or len(response.data) == 0:
            return None
        print("RPC DATA:", response.data)
        print("TYPE:", type(response.data))
        best_result = response.data[0]
        tool_id = best_result.get("tool_id")
        similarity_score = best_result.get("similarity", 0.0)

        if not tool_id:
            return None

        tool = await self.db.get(tool_id)
        if not tool:
            return None

        return ToolSearchResult(
            tool=tool,
            similarity_score=float(similarity_score),
            match_type=""
        )

    async def add(self, tool_id: str, embedding: list[float]):
        """Add or update tool embedding."""
        response = self.supabase.table("tool_embeddings").upsert({
            "tool_id": tool_id,
            "embedding": embedding
        }).execute()

        if response.data:
            log.debug("search.embedding_added", tool_id=tool_id)
        else:
            log.error("search.embedding_failed", tool_id=tool_id)
