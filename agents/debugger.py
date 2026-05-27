"""Autonomous debug agent for fixing tool errors."""
import structlog
from core.config import get_settings

log = structlog.get_logger()
settings = get_settings()


class ToolDebugger:
    def __init__(self):
        self._init_llm()

    def _init_llm(self):
        if settings.llm_provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    async def fix(self, code: str, errors: list) -> str:
        """Fix identified errors in tool code."""
        error_text = "\n".join(
            [f"- [{e.get('severity', 'unknown').upper()}] {e.get('message', 'Unknown error')}" for e in errors]
        )

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
        else:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            fixed_code = response.choices[0].message.content

        log.info("debugger.code_fixed", lines=len(fixed_code.split("\n")))
        return fixed_code
