"""Parse natural language into structured intent."""
from __future__ import annotations

import json
import re
import structlog

from core.config import get_settings
from core.gemini_service import GeminiService

log = structlog.get_logger()


def _extract_json(text: str) -> dict:
    """Robustly extract the first JSON object from `text`, stripping any
    markdown code fences the LLM may have added despite instructions."""
    # Strip markdown fences first — do this in one pass rather than a
    # sequence of fragile string replacements that can interact badly.
    cleaned = re.sub(
        r"```(?:json)?\s*\n?",  # opening fence: ```json or ```
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\n?```", "", cleaned)  # closing fence
    cleaned = cleaned.strip()

    # Find the outermost {...} block — handles cases where the LLM adds a
    # preamble sentence before the JSON.
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON object found in LLM response: {text[:300]}")

    return json.loads(json_match.group())


INTENT_PROMPT = """Extract the intent from the user command below and return a single JSON object.

RULES:
- "inputs" must contain the ACTUAL DATA VALUES from the command — not schema definitions.
- Input key names must be concrete, snake_case, and describe the data (e.g. "sales_data_csv", "target_column").
- Never use meta-fields like "type", "description", "required", or "default" inside inputs.
- If the command contains data inline (CSV, JSON, a list of values), embed it verbatim in inputs.
- If no actual input values are present in the command, return an empty object for inputs.
- "dependencies" should list third-party Python packages the tool will likely need (e.g. ["pandas"]).
  Use the PyPI package name (e.g. "PyYAML" not "yaml", "Pillow" not "PIL").
  Return [] if only stdlib is needed.

RETURN FORMAT (JSON only, no markdown fences, no explanation):
{{
  "name": "tool_name_snake_case",
  "description": "One-sentence description of what the tool does.",
  "category": "data_analysis | file | util | convert | workflow",
  "inputs": {{}},
  "dependencies": []
}}

USER COMMAND:
{user_input}
"""


class IntentParser:
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

    async def parse(self, user_input: str) -> dict:
        """Convert natural-language command to structured intent dict."""
        prompt = INTENT_PROMPT.format(user_input=user_input)

        try:
            settings = get_settings()
            response_text = await self._call_llm(prompt, settings)

            log.info(
                "intent_parser.raw_response",
                provider=settings.llm_provider,
                text_repr=repr(response_text[:400]),
            )

            intent = _extract_json(response_text)

            # Sanity-check required keys — fill defaults rather than crashing.
            intent.setdefault("name", "tool")
            intent.setdefault("description", user_input)
            intent.setdefault("category", "workflow")
            intent.setdefault("inputs", {})
            intent.setdefault("dependencies", [])

            log.info("intent.parsed", intent=intent)
            return intent

        except Exception as e:
            log.error("intent_parser.error", err=str(e))
            return {
                "name": "tool",
                "description": user_input,
                "category": "workflow",
                "inputs": {},
                "dependencies": [],
            }

    async def _call_llm(self, prompt: str, settings) -> str:
        if settings.llm_provider == "anthropic":
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        elif settings.llm_provider == "gemini":
            response = self.client.generate(prompt)
            response_text = getattr(response, "text", None)
            if not isinstance(response_text, str):
                raise ValueError(
                    f"Gemini returned non-string text: {type(response_text).__name__}"
                )
            return response_text

        else:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content


async def parse_intent(user_input: str) -> dict:
    parser = IntentParser()
    return await parser.parse(user_input)