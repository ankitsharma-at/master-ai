"""Code validation agent."""
import json
import re
import structlog
from registry.schemas import CriticResult
from core.config import get_settings

log = structlog.get_logger()


class ToolCritic:
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

    async def validate(self, code: str, tool_meta: dict) -> CriticResult:
        """Validate generated code."""
        prompt = f"""Analyze this code. Respond with ONLY JSON (no markdown):
{{"passed": bool, "reliability_score": 0-100, "issues": [{{"severity": "critical|major|minor", "message": "...", "fix_hint": "..."}}]}}

Check: run(inputs) function exists, has try/except, no hardcoded secrets, no shell injection.

Code:
{code}"""

        log.info("critic.validating")

        try:
            if get_settings().llm_provider == "anthropic":
                response = self.client.messages.create(
                    model=get_settings().llm_model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=get_settings().llm_model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.choices[0].message.content

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
            else:
                result_data = json.loads(response_text)

            passed = result_data.get("passed", False)
            reliability_score = result_data.get("reliability_score", 0)
            settings = get_settings()

            if reliability_score < settings.min_reliability_score:
                passed = False

            return CriticResult(
                passed=passed,
                reliability_score=reliability_score,
                issues=result_data.get("issues", []),
                summary=result_data.get("summary", ""),
            )

        except Exception as e:
            log.error("critic.parse_error", err=str(e))
            return CriticResult(passed=False, reliability_score=0, issues=[{"severity": "critical", "message": "Validation failed"}])
