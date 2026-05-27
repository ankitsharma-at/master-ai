print("Verifying Autonomous AI OS build...")
import sys
sys.path.insert(0, '.')

errors = []

try:
    from core.config import get_settings
    print("✓ core.config loads")
    settings = get_settings()
    assert settings.reuse_threshold == 0.85
    print(f"  Config: thresholds {settings.reuse_threshold}/{settings.adapt_threshold}")
except Exception as e:
    errors.append(f"core.config: {e}")

try:
    from registry.schemas import ToolRecord, ToolSearchResult, CriticResult
    print("✓ registry.schemas loads")
except Exception as e:
    errors.append(f"registry.schemas: {e}")

try:
    from registry.db import ToolRegistryDB
    print("✓ registry.db loads")
except Exception as e:
    errors.append(f"registry.db: {e}")

try:
    from registry.embedder import ToolEmbedder
    print("✓ registry.embedder loads")
except Exception as e:
    errors.append(f"registry.embedder: {e}")

try:
    from registry.search import ToolSearcher
    print("✓ registry.search loads")
except Exception as e:
    errors.append(f"registry.search: {e}")

try:
    from memory.schemas import EpisodicEntry, WorkingMemory
    print("✓ memory.schemas loads")
except Exception as e:
    errors.append(f"memory.schemas: {e}")

try:
    from memory.episodic import EpisodicMemory
    print("✓ memory.episodic loads")
except Exception as e:
    errors.append(f"memory.episodic: {e}")

try:
    from memory.working import WorkingMemoryManager
    print("✓ memory.working loads")
except Exception as e:
    errors.append(f"memory.working: {e}")

try:
    from execution.sandbox import SandboxExecutor
    print("✓ execution.sandbox loads")
except Exception as e:
    errors.append(f"execution.sandbox: {e}")

try:
    from execution.loader import ToolLoader
    print("✓ execution.loader loads")
except Exception as e:
    errors.append(f"execution.loader: {e}")

try:
    from core.intent_parser import parse_intent
    print("✓ core.intent_parser loads")
except Exception as e:
    errors.append(f"core.intent_parser: {e}")

try:
    from core.router import route_request
    print("✓ core.router loads")
except Exception as e:
    errors.append(f"core.router: {e}")

try:
    from core.orchestrator import Orchestrator
    print("✓ core.orchestrator loads")
except Exception as e:
    errors.append(f"core.orchestrator: {e}")

try:
    from agents.generator import ToolGenerator
    print("✓ agents.generator loads")
except Exception as e:
    errors.append(f"agents.generator: {e}")

try:
    from agents.critic import ToolCritic
    print("✓ agents.critic loads")
except Exception as e:
    errors.append(f"agents.critic: {e}")

try:
    from api.main import app
    print("✓ api.main loads")
except Exception as e:
    errors.append(f"api.main: {e}")

if errors:
    print("\n✗ Build errors:")
    for error in errors:
        print(f"  {error}")
    sys.exit(1)
else:
    print("\n" + "="*60)
    print("✅ ALL MODULES LOADED SUCCESSFULLY!")
    print("="*60)
    print("\nProject is ready to run:")
    print("  uvicorn api.main:app --reload")
    print("\nThen visit:")
    print("  http://localhost:8000/health/")
    sys.exit(0)
