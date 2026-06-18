"""Autonomous debug agent for fixing tool errors."""
import structlog
from core.config import get_settings
from core.gemini_service import GeminiService

log = structlog.get_logger()
settings = get_settings()


class ToolDebugger:
    def __init__(self):
        self._init_llm()

    def _init_llm(self):
        if settings.llm_provider == "anthropic":
            from anthropic import Anthropicmaster
        elif settings.llm_provider == "gemini":
            self.client = GeminiService()

        prompt = f"""You are an expert debugger. Fix these errors in the code.

ERRORS TO FIX:
{error_text}

CODE:
{code}

Output ONLY the corrected Python code. No markdown fences. No explanation."""

        log.info("debugger.fixing", error_count=len(errors))

        if settings.llm_provider == "anthropic":
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            fixed_code = response.content[0].text
        elif settings.llm_provider == "gemini":
            response = self.client.generate( prompt )
        else:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            fixed_code = response.choices[0].message.content

        log.info("debugger.code_fixed", lines=len(fixed_code.split("\n")))
        return fixed_code
