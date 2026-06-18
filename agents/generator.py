"""LLM-powered code generation."""
import json
import structlog
from typing import Tuple
from core.config import get_settings
from core.gemini_service import GeminiService
import re

log = structlog.get_logger()


class ToolGenerator:
    def __init__(self):
        self._init_llm()

    def _init_llm(self):
        settings = get_settings()
        if settings.llm_provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        elif settings.llm_provider == "gemini":
            self.client = GeminiService()
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    async def generate(self, intent: dict) -> Tuple[str, dict]:
        """Generate tool code from intent."""
        spec = json.dumps(intent, indent=2)
        prompt = f"""Write a Python tool with run(inputs: dict) -> dict that {intent.get('description', '')}.
Return {{"success": bool, "output": any, "error": str}}.
Include error handling..
Write a Python tool.

IMPORTANT:
- Return ONLY executable Python code.
- DO NOT use markdown.
- DO NOT use ```python fences.
- DO NOT use ``` fences.
- First line must be Python code.
- Last line must be Python code.

Task: {spec}"""

        log.info("generator.calling_llm")

        settings = get_settings()
        if settings.llm_provider == "anthropic":
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            code = response.content[0].text
        elif settings.llm_provider == "gemini":
            response = self.client.generate(prompt)
            code = response.text
            code = self._clean_code(code)

            try:
              self._validate_code(code)
            except SyntaxError as e:
                log.error(
                "generator.invalid_code",
                error=str(e)
            )
                raise
        else:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            code = response.choices[0].message.content
            
        tool_meta = {
            "name": intent.get("name", "generated_tool"),
            "description": intent.get("description", ""),
            "category": intent.get("category", "workflow"),
            "language": "python",
        }

        log.info("generator.code_generated", lines=len(code.split("\n")))
        return code, tool_meta
    def _clean_code(self, code: str) -> str:
        code = code.strip()

        code = re.sub(
            r"^```(?:python|py)?\s*",
            "",
            code,
            flags=re.IGNORECASE,
        )

        code = re.sub(
            r"\s*```$",
            "",
            code,
        )

        return code.strip()
    def _validate_code(self, code: str):
        compile(code, "<generated_tool>", "exec")