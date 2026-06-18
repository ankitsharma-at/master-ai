"""Tool adaptation agent - modifies existing tools for new tasks."""
import structlog
from pathlib import Path
from typing import Tuple
from registry.schemas import ToolRecord
from core.config import get_settings
from execution.loader import ToolLoader
from core.gemini_service import GeminiService

log = structlog.get_logger()
settings = get_settings()


class ToolAdapter:
    def __init__(self):
        self._init_llm()
        self.loader = ToolLoader()

    def _init_llm(self):
        if settings.llm_provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        elif settings.llm_provider == "gemini":
             self.client = GeminiService()
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    async def adapt(self, existing_tool: ToolRecord, new_intent: dict) -> Tuple[ToolRecord, str]:
        """Adapt an existing tool to handle a new intent."""
        existing_code = self.loader.load(existing_tool)

        diff_summary = self._summarize_diff(
            existing_tool.description,
            new_intent.get("description", "")
        )

        prompt = f"""You are a tool adaptation specialist. Modify this existing tool to handle a new task.

EXISTING TOOL CODE:
{existing_code}

NEW TASK: {new_intent.get('description', '')}

DIFFERENCES: {diff_summary}

Adapt the tool to handle the new task while preserving what still works.
Output ONLY the adapted Python code. No markdown fences. No explanation."""

        log.info("adapter.adapting", tool=existing_tool.name)

        if settings.llm_provider == "anthropic":
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            adapted_code = response.content[0].text
        elif settings.llm_provider == "gemini":
            response = self.client.generate(prompt)
            adapted_code = response.text
        else:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            adapted_code = response.choices[0].message.content

        log.info("adapter.done", tool=existing_tool.name)
        return existing_tool, adapted_code

    def _summarize_diff(self, old_desc: str, new_desc: str) -> str:
        return f"Original: {old_desc}\nNew: {new_desc}"
