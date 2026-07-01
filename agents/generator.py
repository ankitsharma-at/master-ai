from __future__ import annotations
"""LLM-powered code generation."""
import json
import structlog
from typing import Tuple
from core.config import get_settings
from core.gemini_service import GeminiService
import re
import ast
import sys
from dataclasses import dataclass

import structlog
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
            dependencies = reconcile_with_reported(code)
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
            "dependencies": dependencies
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




"""Extracts third-party dependencies directly from generated tool code via
static analysis, instead of trusting an LLM-reported `dependencies` list.

Why not just ask the LLM: self-reported dependency lists from a generator
agent are unreliable — they can hallucinate packages, omit transitive
imports, or report the wrong PyPI name for an import (e.g. `cv2` instead of
`opencv-python`). Parsing the actual `import` statements in the generated
code is closer to ground truth and costs no extra LLM call.

This module is intentionally side-effect free: it only inspects source code
as text via `ast`, and never imports or executes anything from the tool.
"""

log = structlog.get_logger()

# Import-name -> PyPI package name, for the common cases where they differ.
# Extend this table as you discover more mismatches in generated tools.
IMPORT_TO_PACKAGE: dict[str, str] = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "Crypto": "pycryptodome",
    "jwt": "PyJWT",
    "dateutil": "python-dateutil",
    "google": "google-api-python-client",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "fitz": "PyMuPDF",
    "skimage": "scikit-image",
}

# Modules that exist in the standard library across supported Python
# versions, so they should never trigger a pip install. Using
# sys.stdlib_module_names (3.10+) as the primary source, with a small
# manual top-up for names that don't always show up there.
_STDLIB_EXTRA = {
    "__future__", "dataclasses", "typing_extensions", "_typeshed",
}

try:
    STDLIB_MODULES: set[str] = set(sys.stdlib_module_names) | _STDLIB_EXTRA  # type: ignore[attr-defined]
except AttributeError:
    # Python < 3.10 fallback — a reasonably complete manual list of the
    # modules likely to show up in generated tool code.
    STDLIB_MODULES = {
        "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect",
        "calendar", "collections", "contextlib", "copy", "csv", "dataclasses",
        "datetime", "decimal", "difflib", "enum", "functools", "glob",
        "hashlib", "heapq", "hmac", "html", "http", "io", "itertools", "json",
        "logging", "math", "mimetypes", "multiprocessing", "operator", "os",
        "pathlib", "pickle", "pprint", "queue", "random", "re", "secrets",
        "shutil", "signal", "socket", "sqlite3", "stat", "statistics",
        "string", "struct", "subprocess", "sys", "tempfile", "textwrap",
        "threading", "time", "traceback", "typing", "unicodedata",
        "urllib", "uuid", "warnings", "xml", "zipfile",
    } | _STDLIB_EXTRA

# Names that resolve to local/internal modules within the sandbox's own
# project layout (e.g. the generated tool's own helper modules, or names
# the runner injects) — never treat these as pip-installable.
INTERNAL_MODULES = {"tool", "runner"}


@dataclass
class DependencyExtractionResult:
    # Final, deduped, pip-installable package names (already mapped from
    # import name -> PyPI name where needed).
    packages: list[str]
    # Raw top-level import names found in the code, before stdlib filtering
    # or PyPI-name mapping — useful for logging/debugging.
    raw_imports: list[str]
    # Imports that were skipped because they couldn't be parsed as a clean
    # static import (e.g. inside a try/except ImportError guard) — surfaced
    # so callers can decide whether to log a warning.
    uncertain: list[str]


def extract_dependencies(code: str) -> DependencyExtractionResult:
    """Parse `code` and return the third-party packages it imports.

    Only looks at top-level `import x` / `from x import y` statements
    (and submodule imports like `import x.y`, which resolve to package `x`).
    Relative imports (`from . import foo`) are ignored since they can only
    refer to local/internal modules, never a pip package.
    """
    raw_imports: set[str] = set()
    uncertain: set[str] = set()

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        log.warning("dependency_extraction.syntax_error", error=str(e))
        return DependencyExtractionResult(packages=[], raw_imports=[], uncertain=[])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                raw_imports.add(top_level)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Relative import (`from . import x`) — always local, skip.
                continue
            if node.module is None:
                continue
            top_level = node.module.split(".")[0]
            raw_imports.add(top_level)

    packages: set[str] = set()
    for name in raw_imports:
        if name in STDLIB_MODULES or name in INTERNAL_MODULES:
            continue
        packages.add(IMPORT_TO_PACKAGE.get(name, name))

    return DependencyExtractionResult(
        packages=sorted(packages),
        raw_imports=sorted(raw_imports),
        uncertain=sorted(uncertain),
    )


def reconcile_with_reported(
    code: str,
    reported: list[str] | None,
) -> list[str]:
    """Combine statically-extracted deps with whatever the generator agent
    reported, preferring the static result but keeping any reported package
    that wasn't caught by static analysis (e.g. a dependency only needed by
    a dynamic `importlib.import_module(...)` call).

    This is the function `agents/generator.py` should call right after
    generating code, instead of trusting `tool_meta.dependencies` as-is.
    """
    extracted = extract_dependencies(code)
    reported_set = set(reported or [])
    extracted_set = set(extracted.packages)

    only_reported = reported_set - extracted_set
    if only_reported:
        log.info(
            "dependency_reconcile.reported_only",
            packages=sorted(only_reported),
            note="kept; not found via static analysis (may be dynamic imports)",
        )

    return sorted(extracted_set | reported_set)