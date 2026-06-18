"""Direct LLM execution for simple tasks."""
import json
import re
import structlog
from typing import Any
from core.config import get_settings
from core.gemini_service import GeminiService

log = structlog.get_logger()


class DirectLLMExecutor:
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

    async def execute(self, user_input: str, intent: dict) -> dict:
        """
        Execute simple task directly with LLM.
        Returns: {"success": bool, "output": any, "error": str}
        """
        category = intent.get("category", "general")

        prompt = self._build_prompt(user_input, intent, category)

        try:
            settings = get_settings()
            if settings.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=settings.llm_model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = response.content[0].text
            elif settings.llm_provider == "gemini":
                response = self.client.generate(prompt)
                result_text = response.text
            else:
                response = self.client.chat.completions.create(
                    model=settings.llm_model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = response.choices[0].message.content

            log.info("direct_llm.executed", category=category)

            return {"success": True, "output": self._extract_output(result_text, category), "error": None}

        except Exception as e:
            log.error("direct_llm.error", err=str(e))
            return {"success": False, "output": None, "error": str(e)}

    def _build_prompt(self, user_input: str, intent: dict, category: str) -> str:
        """Build prompt based on task category."""
        base = f"""Task: {user_input}

"""

        if category == "text_processing":
            return base + """Process this text task and provide the result.
Output should be directly usable (no explanations unless asked).
Focus on the task output."""

        elif category == "data_analysis":
            return base + """Analyze this data as requested.
Provide clear, structured output.
Use JSON format if appropriate."""

        elif category == "qa":
            return base + """Answer this question accurately and concisely.
Provide direct answer without excessive preamble."""

        elif category == "code_review":
            return base + """Review and provide feedback.
Format: List specific issues and improvements."""

        elif category == "explanation":
            return base + """Explain this concept clearly.
Be thorough but concise."""

        else:
            return base + """Complete this task.
Provide the result directly without excessive explanation."""

    def _extract_output(self, result_text: str, category: str) -> Any:
        """Extract and format output based on category."""
        if category in ["data_analysis"]:
            json_match = re.search(r"\[.*\]|\{.*\}", result_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass

        return result_text.strip()
