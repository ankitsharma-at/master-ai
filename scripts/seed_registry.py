"""Pre-populate registry with starter tools."""
import asyncio
import structlog
from pathlib import Path
from registry.db import ToolRegistryDB
from registry.embedder import ToolEmbedder
from registry.search import ToolSearcher
from execution.loader import ToolLoader

log = structlog.get_logger()


STARTER_TOOLS = [
    {
        "name": "text_summarizer",
        "description": "Summarize long text into key points",
        "category": "ai_pipeline",
        "language": "python",
        "code": """
import json

def run(inputs):
    try:
        text = inputs.get('text', '')
        lines = text.split('\\n')
        summary = '\\n'.join(lines[:min(3, len(lines))])
        return {
            'success': True,
            'output': {'summary': summary},
            'error': None
        }
    except Exception as e:
        return {'success': False, 'output': None, 'error': str(e)}
""",
    },
    {
        "name": "json_formatter",
        "description": "Format and validate JSON data",
        "category": "data_pipeline",
        "language": "python",
        "code": """
import json

def run(inputs):
    try:
        data = inputs.get('data', {})
        formatted = json.dumps(data, indent=2)
        return {
            'success': True,
            'output': {'formatted': formatted},
            'error': None
        }
    except Exception as e:
        return {'success': False, 'output': None, 'error': str(e)}
""",
    },
    {
        "name": "email_validator",
        "description": "Validate email addresses and extract domain info",
        "category": "data_pipeline",
        "language": "python",
        "code": """
import re

def run(inputs):
    try:
        email = inputs.get('email', '')
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        valid = bool(re.match(pattern, email))

        if valid:
            domain = email.split('@')[1]
            return {
                'success': True,
                'output': {
                    'valid': True,
                    'domain': domain,
                    'email': email
                },
                'error': None
            }
        else:
            return {
                'success': True,
                'output': {'valid': False, 'email': email},
                'error': None
            }
    except Exception as e:
        return {'success': False, 'output': None, 'error': str(e)}
""",
    },
]


async def seed_registry():
    """Populate registry with starter tools."""
    db = ToolRegistryDB()
    embedder = ToolEmbedder()
    searcher = ToolSearcher()
    loader = ToolLoader()

    log.info("seed.starting", count=len(STARTER_TOOLS))

    for tool_spec in STARTER_TOOLS:
        existing = await db.get_by_name(tool_spec["name"])
        if existing:
            log.info("seed.skipping", tool=tool_spec["name"], reason="already exists")
            continue

        tool = await db.create(tool_spec, reliability_score=90)
        loader.save(tool, tool_spec["code"])

        embedding = embedder.embed(tool.description)
        await searcher.add(tool.id, embedding)

        log.info("seed.added", tool=tool.name, id=tool.id)

    log.info("seed.complete", count=len(STARTER_TOOLS))


if __name__ == "__main__":
    asyncio.run(seed_registry())
