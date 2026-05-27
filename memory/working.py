"""Working memory for per-request state."""
from memory.schemas import WorkingMemory
import structlog

log = structlog.get_logger()


class WorkingMemoryManager:
    def __init__(self):
        self.sessions = {}

    def create(self, session_id: str, intent: dict) -> WorkingMemory:
        """Create a new working memory context."""
        wm = WorkingMemory(
            session_id=session_id,
            intent=intent.get("description", ""),
            entities=intent.get("entities", {}),
            subtasks=intent.get("subtasks", []),
        )
        self.sessions[session_id] = wm
        log.debug("working_memory.created", session=session_id)
        return wm

    def get(self, session_id: str) -> WorkingMemory:
        """Retrieve working memory for a session."""
        return self.sessions.get(session_id)

    def update(self, session_id: str, **kwargs):
        """Update working memory fields."""
        wm = self.sessions.get(session_id)
        if wm:
            for key, value in kwargs.items():
                if hasattr(wm, key):
                    setattr(wm, key, value)

    def add_intermediate_result(self, session_id: str, result: any):
        """Add an intermediate result to working memory."""
        wm = self.sessions.get(session_id)
        if wm:
            wm.intermediate_results.append(result)

    def clear(self, session_id: str):
        """Clear working memory for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            log.debug("working_memory.cleared", session=session_id)
