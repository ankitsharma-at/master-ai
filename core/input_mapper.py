"""Maps raw intent inputs to a tool's stored input_schema.

The problem this solves:
  - The intent parser extracts actual data values from the user's command.
  - The selected tool (especially on REUSE) has a stored input_schema with
    specific key names the tool's run(inputs) function expects.
  - These key names may differ: the user says "sales data" and the intent
    parser calls it "sales_data_csv", but the reused tool expects "csv_data".
  - Without this mapping step, the sandbox receives incorrectly-keyed inputs
    and the tool fails or silently ignores the data.

Strategy:
  1. If the intent's keys already match the schema exactly → pass through.
  2. If there's a mismatch → use an LLM call to map the raw intent data into
     the schema's expected keys. This is a tiny, cheap, focused prompt
     (much cheaper than generating a whole tool) and only fires on mismatch.
  3. If the schema is empty (new generated tool) → pass intent inputs as-is,
     since the generator wrote the code to match those exact keys.

This module is intentionally stateless — no DB calls, no side effects.
"""
from __future__ import annotations

import json
import re
import structlog

from core.config import get_settings
from core.gemini_service import GeminiService

log = structlog.get_logger()


def _keys_match(intent_inputs: dict, schema: dict) -> bool:
    """True if intent_inputs already has exactly the keys the schema expects."""
    if not schema:
        return True  # no schema = generated tool, pass through
    schema_keys = set(schema.keys())
    intent_keys = set(intent_inputs.keys())
    return schema_keys == intent_keys


def _build_mapping_prompt(
    schema: dict,
    intent_inputs: dict,
    tool_name: str,
    tool_description: str,
) -> str:
    # Show schema keys with their types so the LLM understands the shape
    schema_summary = "\n".join(
        f'  "{k}": {v}' for k, v in schema.items()
    )
    # Show raw intent data — full values so the LLM can assign them correctly
    intent_summary = json.dumps(intent_inputs, indent=2)

    return f"""You are mapping user-provided data to the exact input schema expected by a tool.

TOOL: {tool_name}
DESCRIPTION: {tool_description}

TOOL'S EXPECTED INPUT SCHEMA (key name → Python type):
{{{schema_summary}
}}

RAW DATA EXTRACTED FROM USER'S COMMAND:
{intent_summary}

Task: Produce a JSON object whose keys are EXACTLY the schema keys above,
with values taken or derived from the raw data.

Rules:
- Use only the schema key names — no extras, no omissions.
- Assign each value from the raw data to the most semantically matching schema key.
- If a schema key has no matching raw data, use null.
- Return ONLY the JSON object. No markdown fences. No explanation.
"""


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in LLM response: {text[:300]}")
    return json.loads(match.group())


class InputMapper:
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

    async def map_inputs(
        self,
        intent_inputs: dict,
        tool_schema: dict,
        tool_name: str = "tool",
        tool_description: str = "",
    ) -> dict:
        """Return inputs correctly keyed for the tool's schema.

        - If tool_schema is empty → return intent_inputs unchanged (new tool
          path: generator wrote code matching these exact keys).
        - If keys already match → return intent_inputs unchanged (fast path,
          no LLM call).
        - Otherwise → one focused LLM call to remap values to schema keys.
        """
        if not tool_schema:
            log.info("input_mapper.passthrough", reason="no_schema", tool=tool_name)
            return intent_inputs

        if _keys_match(intent_inputs, tool_schema):
            log.info("input_mapper.passthrough", reason="keys_match", tool=tool_name)
            return intent_inputs

        log.info(
            "input_mapper.remapping",
            tool=tool_name,
            intent_keys=list(intent_inputs.keys()),
            schema_keys=list(tool_schema.keys()),
        )

        prompt = _build_mapping_prompt(
            tool_schema, intent_inputs, tool_name, tool_description
        )

        try:
            response_text = await self._call_llm(prompt)
            mapped = _extract_json(response_text)

            # Validate: all schema keys must be present in the result
            missing = set(tool_schema.keys()) - set(mapped.keys())
            if missing:
                log.warning(
                    "input_mapper.missing_keys",
                    missing=missing,
                    falling_back_to_intent_inputs=True,
                )
                # Fill missing keys with None rather than returning broken inputs
                for k in missing:
                    mapped.setdefault(k, None)

            log.info("input_mapper.done", mapped_keys=list(mapped.keys()))
            return mapped

        except Exception as e:
            log.error("input_mapper.error", err=str(e))
            # Don't crash the whole pipeline — fall back to the intent inputs
            # and let the sandbox surface the key mismatch error if it happens.
            return intent_inputs

    async def _call_llm(self, prompt: str) -> str:
        settings = get_settings()

        if settings.llm_provider == "anthropic":
            response = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        elif settings.llm_provider == "gemini":
            response = self.client.generate(prompt)
            text = getattr(response, "text", None)
            if not isinstance(text, str):
                raise ValueError(f"Gemini returned non-string: {type(text)}")
            return text

        else:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content