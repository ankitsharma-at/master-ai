"""Tool code management."""
import os
from pathlib import Path
import structlog
from registry.schemas import ToolRecord
from core.config import get_settings

log = structlog.get_logger()


class ToolLoader:
    def __init__(self):
        settings = get_settings()
        Path(settings.tools_dir).mkdir(parents=True, exist_ok=True)

    def save(self, tool: ToolRecord, code: str):
        """Save tool code to disk."""
        Path(tool.code_path).parent.mkdir(parents=True, exist_ok=True)
        if code.strip().startswith("```"):
            log.warning(
         "loader.markdown_detected",
        tool=tool.name
    )

        with open(tool.code_path, "w", encoding="utf-8") as f:
          f.write(code)
        log.info("loader.saved", tool=tool.name)

    def load(self, tool: ToolRecord) -> str:
        """Load tool code from disk."""
        if not os.path.exists(tool.code_path):
            raise FileNotFoundError(f"Tool not found at {tool.code_path}")
        with open(tool.code_path, "r") as f:
            return f.read()
