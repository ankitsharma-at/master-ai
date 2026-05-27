"""Parse natural language into structured intent."""
import json
import re
import structlog
from core.config import get_settings

log = structlog.get_logger()


class IntentParser:
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

    async def parse(self, user_input: str) -> dict:
        """Convert NL to structured intent."""
        prompt = f"""Extract intent from command. Respond with ONLY JSON (no markdown):
{{"name": "tool_name_snake_case", "description": "...", "category": "workflow", "inputs": {{}}, "dependencies": []}}

Command: {user_input}"""

        try:
            if get_settings().llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=get_settings().llm_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=get_settings().llm_model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.choices[0].message.content

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text)
        except Exception as e:
            log.error("intent_parser.error", err=str(e))
            return {"description": user_input, "name": "tool", "category": "workflow", "inputs": {}}


async def parse_intent(user_input: str) -> dict:
    parser = IntentParser()
    return await parser.parse(user_input)
