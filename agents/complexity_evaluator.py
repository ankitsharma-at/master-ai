"""Evaluate task complexity to decide: tool vs direct LLM."""
import json
import re
import structlog
from core.config import get_settings
from core.gemini_service import GeminiService

log = structlog.get_logger()


class ComplexityEvaluator:
    def __init__(self):
        self._init_llm()

    def _init_llm(self):
        settings = get_settings()
        if settings.llm_provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        elif settings.llm_provider == "gemini":
            from core.gemini_service import GeminiService
            
            self.client = GeminiService()
        else:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    async def evaluate(self, user_input: str, intent: dict) -> dict:
        """
        Evaluate task complexity.
        Returns: {
            "complexity": "simple" | "moderate" | "complex",
            "recommendation": "direct_llm" | "tool",
            "reasoning": "...",
            "estimated_tokens": int
        }
        """
        settings = get_settings()

        # If direct LLM is disabled, always recommend tool
        if not settings.enable_direct_llm:
            return {
                "complexity": "moderate",
                "recommendation": "tool",
                "reasoning": "Direct LLM mode disabled",
                "estimated_tokens": 1000,
            }

        prompt = f"""Analyze this task's complexity for an AI system.

User Request: {user_input}

Task Intent:
{json.dumps(intent, indent=2)}

Rate complexity and recommend approach:
- direct_llm: Simple tasks (Q&A, text transformation, analysis, summarization)
- tool: Complex tasks (requires code, repeated use, file I/O, API calls)

Respond with ONLY JSON (no markdown):
{{
  "complexity": "simple" | "moderate" | "complex",
  "recommendation": "direct_llm" | "tool",
  "reasoning": "Brief explanation",
  "estimated_tokens": 100-10000,
  "factors": ["list", "of", "deciding", "factors"]
}}"""

        try:
            settings = get_settings()
            if settings.llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=settings.llm_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text
            elif settings.llm_provider == "gemini":
                response = self.client.generate(prompt)
                response_text = response.text
            else:
                response = self.client.chat.completions.create(
                    model=settings.llm_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.choices[0].message.content
            print("\n=== COMPLEXITY RAW RESPONSE ===")
            print(response_text)
            print("==============================\n")
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)

            log.info(
                "complexity.evaluated",
                complexity=result.get("complexity"),
                recommendation=result.get("recommendation"),
            )

            return result

        except Exception as e:
            log.error("complexity.error", err=str(e))
            return {
                "complexity": "moderate",
                "recommendation": "tool",
                "reasoning": "Default to tool for safety",
                "estimated_tokens": 1000,
            }
