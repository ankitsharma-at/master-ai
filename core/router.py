"""Router decision logic."""
import structlog
from registry.schemas import ToolSearchResult
from core.config import get_settings

log = structlog.get_logger()


class RouteDecision:
    def __init__(self, match_type: str, similarity_score: float = 0.0):
        self.match_type = match_type
        self.similarity_score = similarity_score


def route_request(search_result: ToolSearchResult, settings) -> RouteDecision:
    """Decide whether to reuse, adapt, or generate."""
    if not search_result:
        return RouteDecision("generate", 0.0)

    score = search_result.similarity_score

    if score >= settings.reuse_threshold:
        log.info("router.reuse", score=round(score, 3))
        return RouteDecision("reuse", score)
    elif score >= settings.adapt_threshold:
        log.info("router.adapt", score=round(score, 3))
        return RouteDecision("adapt", score)
    else:
        log.info("router.generate", score=round(score, 3))
        return RouteDecision("generate", score)
