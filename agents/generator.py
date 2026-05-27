"""LLM-powered code generation."""
import json
import structlog
from typing import Tuple
from core.config import get_settings

log = structlog.get_logger()


class ToolGenerator:
    def __init__(self):
        self._init_llm()

    def _init_llm(self):
        settings = get_settings()
        if settings.llm_provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    async def generate(self, intent: dict) -> Tuple[str, dict]:
        """Generate tool code from intent."""
        spec = json.dumps(intent, indent=2)
        prompt = f"""Write a Python tool with run(inputs: dict) -> dict that {intent.get('description', '')}.
Return {{"success": bool, "output": any, "error": str}}.
Include error handling. Output ONLY raw Python code.

Task: {spec}"""

        log.info("generator.calling_llm")

        if get_settings().llm_provider == "anthropic":
            response = self.client.messages.create(
                model=get_settings().llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            code = response.content[0].text
        else:
            response = self.client.chat.completions.create(
                model=get_settings().llm_model,
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
