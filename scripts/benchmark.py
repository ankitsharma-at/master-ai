"""Measure tool reuse rate and performance over time."""
import asyncio
import structlog
from datetime import datetime
from registry.db import ToolRegistryDB
from supabase import create_client
from core.config import get_settings

log = structlog.get_logger()
settings = get_settings()


async def analyze_registry_stats():
    """Analyze registry statistics."""
    db = ToolRegistryDB()
    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    tools = await db.list()

    total_uses = sum(t.use_count for t in tools)
    total_successes = sum(t.success_count for t in tools)
    avg_reliability = sum(t.reliability_score for t in tools) / len(tools) if tools else 0

    reuse_rate = (total_successes / total_uses * 100) if total_uses > 0 else 0

    # Get usage by match type
    usage_response = supabase.table("tool_usage").select("match_type, COUNT(*)").execute()
    usage_by_type = {}
    for row in usage_response.data:
        match_type = row.get("match_type", "unknown")
        usage_by_type[match_type] = usage_by_type.get(match_type, 0) + row.get("count", 0)

    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_tools": len(tools),
        "total_uses": total_uses,
        "total_successes": total_successes,
        "reuse_rate_percent": round(reuse_rate, 2),
        "avg_reliability_score": round(avg_reliability, 2),
        "usage_by_type": usage_by_type,
        "tools": [
            {
                "name": t.name,
                "uses": t.use_count,
                "successes": t.success_count,
                "reliability": t.reliability_score,
            }
            for t in tools
        ],
    }

    return stats


async def main():
    """Run benchmark."""
    log.info("benchmark.starting")
    stats = await analyze_registry_stats()

    log.info(
        "benchmark.results",
        total_tools=stats["total_tools"],
        reuse_rate=stats["reuse_rate_percent"],
        avg_reliability=stats["avg_reliability_score"],
    )

    print("\n" + "="*60)
    print("REGISTRY STATISTICS")
    print("="*60)
    print(f"  Total Tools: {stats['total_tools']}")
    print(f"  Total Uses: {stats['total_uses']}")
    print(f"  Success Rate: {stats['reuse_rate_percent']}%")
    print(f"  Avg Reliability: {stats['avg_reliability_score']}/100")

    if stats["usage_by_type"]:
        print("\n  Usage by Match Type:")
        for match_type, count in stats["usage_by_type"].items():
            print(f"    {match_type}: {count} executions")

    if stats["tools"]:
        print("\n  Tool Details:")
        for tool in stats["tools"]:
            print(f"    {tool['name']}: {tool['uses']} uses, {tool['successes']} successes, {tool['reliability']}% reliability")

    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
