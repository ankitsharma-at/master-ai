"""Docker sandbox execution.

Design for dependencies:

1. The base sandbox image (`settings.docker_image`) should be built with
   the most commonly needed packages already baked in — requests, pandas,
   numpy, PyYAML, beautifulsoup4, python-dateutil, etc. This keeps the
   common case (REUSE path, most generated tools) at near-zero install
   overhead, which matters for the "100-300ms on reuse" target.

2. For a tool whose dependencies aren't already satisfied by the base
   image, we don't `pip install` inside the container on every single
   run — that would add multi-second overhead to every execution, even
   on REUSE, which defeats the point of caching tools at all.

   Instead, the first time a tool with extra dependencies is executed, we
   build a small derived image (base image + pip install of just that
   tool's deps) and tag it by a hash of the sorted dependency list. Any
   other tool needing the same dependency set reuses that image. Subsequent
   runs of THIS tool also reuse it directly — no install step at all.

3. An explicit allowlist guards what's installable, so a generated tool
   can't smuggle in installation of something unexpected. If a dependency
   isn't on the allowlist, the run fails fast with a clear error instead
   of silently installing arbitrary PyPI packages picked by an LLM.

4. _run_local (Docker unavailable) installs missing dependencies into the
   current Python environment on first use via subprocess pip, then caches
   the installed set in-memory so subsequent runs of the same tool are fast.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Optional

import structlog

from core.config import get_settings
from registry.schemas import ToolRecord

log = structlog.get_logger()

# Packages allowed to be installed. Anything not here causes a fast fail
# rather than silently pip-installing whatever an LLM decided it needed.
ALLOWED_DEPENDENCIES: frozenset[str] = frozenset(
    {
        "requests", "pandas", "numpy", "PyYAML", "beautifulsoup4",
        "python-dateutil", "Pillow", "lxml", "markdown", "pypdf",
        "opencv-python", "python-docx", "python-pptx", "openpyxl",
        "scikit-learn", "scipy", "python-dotenv", "PyJWT", "pydantic",
        "tabulate", "xlrd", "xlwt", "pyarrow", "statsmodels",
    }
)

# Map PyPI package name -> the import name used to check if it's already
# importable (they differ for several common packages).
PACKAGE_TO_IMPORT: dict[str, str] = {
    "PyYAML": "yaml",
    "Pillow": "PIL",
    "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn",
    "python-dateutil": "dateutil",
    "python-dotenv": "dotenv",
    "PyJWT": "jwt",
    "opencv-python": "cv2",
    "python-docx": "docx",
    "python-pptx": "pptx",
}

# In-process cache: set of package names already confirmed importable so
# we don't re-check on every local run.
_locally_installed: set[str] = set()


class ExecutionResult:
    def __init__(self, success: bool, output: Any = None, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.error = error


def _deps_image_tag(base_image: str, dependencies: list[str]) -> str:
    """Deterministic Docker image tag for a given dependency set."""
    digest = hashlib.sha256(",".join(sorted(dependencies)).encode()).hexdigest()[:16]
    safe_base = base_image.replace("/", "-").replace(":", "-")
    return f"ai-os-sandbox-{safe_base}-{digest}"


def _is_importable(package: str) -> bool:
    """Check if `package` is already importable in the current environment."""
    import_name = PACKAGE_TO_IMPORT.get(package, package)
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def _pip_install(packages: list[str]) -> None:
    """Install `packages` into the current Python environment via pip.
    Raises RuntimeError on failure."""
    log.info("sandbox.local.pip_install", packages=packages)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", *packages],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pip install failed for {packages}:\n{result.stderr}"
        )
    log.info("sandbox.local.pip_install_done", packages=packages)


def _ensure_local_dependencies(dependencies: list[str]) -> None:
    """Install any dependencies from `dependencies` that aren't yet importable.

    Uses _locally_installed as an in-process cache so repeated runs of the
    same tool don't shell out to pip every time — only the very first run
    of a tool with new deps pays the install cost.
    """
    if not dependencies:
        return

    disallowed = [d for d in dependencies if d not in ALLOWED_DEPENDENCIES]
    if disallowed:
        raise ValueError(
            f"Dependencies not on the allowlist, refusing to install: {disallowed}. "
            f"Add them to ALLOWED_DEPENDENCIES in sandbox.py if intentional."
        )

    to_install = [
        pkg for pkg in dependencies
        if pkg not in _locally_installed and not _is_importable(pkg)
    ]

    if to_install:
        _pip_install(to_install)
        # After a successful install, invalidate importlib's cache so the
        # newly-installed packages are findable without a process restart.
        importlib.invalidate_caches()

    # Mark all as confirmed regardless of whether we just installed them or
    # they were already there — avoids re-checking on the next run.
    _locally_installed.update(dependencies)


class SandboxExecutor:
    def __init__(self):
        try:
            import docker
            self.client = docker.from_env()
            self.docker_available = True
        except Exception:
            self.client = None
            self.docker_available = False
            log.warning("sandbox.docker_unavailable - running in local mode (not a real sandbox)")

    # ------------------------------------------------------------------
    # Dependency image resolution (Docker path)
    # ------------------------------------------------------------------

    def _validate_dependencies(self, dependencies: list[str]) -> list[str]:
        disallowed = [d for d in dependencies if d not in ALLOWED_DEPENDENCIES]
        if disallowed:
            raise ValueError(
                f"Dependencies not on the allowlist, refusing to install: {disallowed}."
            )
        return dependencies

    def _ensure_dependency_image(self, base_image: str, dependencies: list[str]) -> str:
        """Return image tag to use: base image if no extra deps, otherwise a
        cached derived image with those deps pre-installed."""
        if not dependencies:
            return base_image

        self._validate_dependencies(dependencies)
        tag = _deps_image_tag(base_image, dependencies)

        try:
            self.client.images.get(tag)
            log.info("sandbox.dependency_image_cache_hit", tag=tag)
            return tag
        except Exception:
            pass

        log.info("sandbox.dependency_image_building", tag=tag, dependencies=dependencies)
        dockerfile = (
            f"FROM {base_image}\n"
            f"RUN pip install --no-cache-dir {' '.join(dependencies)}\n"
        )
        with tempfile.TemporaryDirectory() as build_dir:
            with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
                f.write(dockerfile)
            self.client.images.build(path=build_dir, tag=tag, rm=True)

        log.info("sandbox.dependency_image_built", tag=tag)
        return tag

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, code: str, tool: ToolRecord, inputs: dict) -> ExecutionResult:
        """Execute tool in sandbox."""
        dependencies = list(getattr(tool, "dependencies", None) or [])

        if not self.docker_available:
            return await self._run_local(code, inputs, dependencies)

        settings = get_settings()
        try:
            image_tag = self._ensure_dependency_image(settings.docker_image, dependencies)
        except Exception as e:
            log.error("sandbox.dependency_resolution_failed", error=str(e))
            return ExecutionResult(False, None, f"Dependency setup failed: {e}")

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "tool.py"), "w") as f:
                f.write(code)
            with open(os.path.join(tmpdir, "inputs.json"), "w") as f:
                json.dump(inputs, f)

            runner = """
import json, sys
sys.path.insert(0, '/workspace')
from tool import run
with open('/workspace/inputs.json') as f:
    inputs = json.load(f)
try:
    result = run(inputs)
    print("__RESULT_START__")
    print(json.dumps(result))
    print("__RESULT_END__")
except Exception as e:
    import traceback
    print("__RESULT_START__")
    print(json.dumps({"success": False, "output": None, "error": f"{e}\\n{traceback.format_exc()}"}))
    print("__RESULT_END__")
"""
            with open(os.path.join(tmpdir, "runner.py"), "w") as f:
                f.write(runner)

            container = None
            try:
                container = self.client.containers.run(
                    image=image_tag,
                    command="python /workspace/runner.py",
                    volumes={tmpdir: {"bind": "/workspace", "mode": "ro"}},
                    mem_limit=settings.sandbox_memory_limit,
                    network_disabled=True,
                    detach=True,
                )
                container.wait(timeout=settings.sandbox_timeout_seconds)
                raw_logs = container.logs(stdout=True, stderr=True).decode(errors="replace")

                if "__RESULT_START__" in raw_logs and "__RESULT_END__" in raw_logs:
                    payload = (
                        raw_logs
                        .split("__RESULT_START__", 1)[1]
                        .split("__RESULT_END__", 1)[0]
                        .strip()
                    )
                    result = json.loads(payload)
                    return ExecutionResult(
                        result.get("success", False),
                        result.get("output"),
                        result.get("error"),
                    )

                return ExecutionResult(
                    False, None,
                    f"No result markers in container output. Logs: {raw_logs[:2000]}"
                )

            except Exception as e:
                log.error("sandbox.docker_error", error=str(e), traceback=traceback.format_exc())
                return ExecutionResult(False, None, str(e))

            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

    async def _run_local(
        self, code: str, inputs: dict, dependencies: list[str] | None = None
    ) -> ExecutionResult:
        """Fallback when Docker isn't available. Runs the generated code
        directly in-process after installing any missing dependencies.

        NOT a real sandbox — only for local development. Any tool code
        executed here runs with full access to the host environment.
        """
        try:
            _ensure_local_dependencies(dependencies or [])
        except Exception as e:
            log.error("sandbox.local.dep_install_failed", error=str(e))
            return ExecutionResult(False, None, f"Dependency install failed: {e}")

        try:
            exec_globals: dict[str, Any] = {}
            exec(code, exec_globals)
            result = exec_globals["run"](inputs)

            return ExecutionResult(
                result.get("success", False),
                result.get("output"),
                result.get("error"),
            )

        except Exception as e:
            log.error(
                "sandbox.local_error",
                error=str(e),
                traceback=traceback.format_exc(),
            )
            return ExecutionResult(False, None, str(e))