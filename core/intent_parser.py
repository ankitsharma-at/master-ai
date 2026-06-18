"""Parse natural language into structured intent."""
import json
import re
import structlog
from core.config import get_settings
from core.gemini_service import GeminiService
log = structlog.get_logger()


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
        """Convert NL to structured intent."""
        prompt = f"""
Extract intent from the command.

Return ONLY valid JSON.

Rules:
- inputs must contain ACTUAL VALUES extracted from the command.
- Never generate input schemas.
- Never generate fields like type, description, required, default.
- If no actual values are present, return an empty object for inputs.

Format:

{{
  "name": "tool_name_snake_case",
  "description": "...",
  "category": "workflow",
  "inputs": {{}},
  "dependencies": []
}}

Command:
{user_input}
"""

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
                log.info(
                    "gemini.response.debug",
                    response_type=type(response).__name__,
                    response_repr=repr(response)
                    )

                response_text = getattr(response, "text", None)

                log.info(
                    "gemini.text.debug",
                    text_type=type(response_text).__name__,
                    text_repr=repr(response_text)
                )
                if not isinstance(response_text, str):
                    raise ValueError(
                    f"Gemini returned non-string text: {type(response_text).__name__}"
                    )
            else:
                response = self.client.chat.completions.create(
                    model=settings.llm_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.choices[0].message.content
            # intent = json.loads(response_text)

            cleaned = response_text.strip()

            cleaned = cleaned.replace("`json", "")
            cleaned = cleaned.replace("```json", "")
            cleaned = cleaned.replace("```", "")
            cleaned = cleaned.replace("`", "")
            cleaned = cleaned.strip()
            cleaned = re.sub(
                r"^```(?:json)?|```$",
                "",
                cleaned,
                flags=re.MULTILINE
            ).strip()

            json_match = re.search(
                r"\{.*\}",
                cleaned,
                re.DOTALL
            )

            if json_match:
                intent = json.loads(json_match.group())

                log.info(
                "intent.parsed",
                intent=intent
                )

                return intent

            return json.loads(cleaned)
            
        except Exception as e:
            log.error("intent_parser.error", err=str(e))
            return {"description": user_input, "name": "tool", "category": "workflow", "inputs": {},"dependencies": []
}


async def parse_intent(user_input: str) -> dict:
    parser = IntentParser()
    return await parser.parse(user_input)
