"""Docker sandbox execution."""
import json
import tempfile
import os
import structlog
from core.config import get_settings
from registry.schemas import ToolRecord

log = structlog.get_logger()


class ExecutionResult:
    def __init__(self, success: bool, output: any, error: str = None):
        self.success = success
        self.output = output
        self.error = error


class SandboxExecutor:
    def __init__(self):
        try:
            import docker
            self.client = docker.from_env()
        except:
            self.client = None
            log.warning("sandbox.docker_unavailable")

    async def run(self, code: str, tool: ToolRecord, inputs: dict) -> ExecutionResult:
        """Execute tool in sandbox."""
        if not self.client:
            return await self._run_local(code, inputs)

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
print(json.dumps(run(inputs)))
"""
            with open(os.path.join(tmpdir, "runner.py"), "w") as f:
                f.write(runner)

            try:
                settings = get_settings()
                output = self.client.containers.run(
                    image=settings.docker_image,
                    command="python /workspace/runner.py",
                    volumes={tmpdir: {"bind": "/workspace", "mode": "ro"}},
                    mem_limit=settings.sandbox_memory_limit,
                    remove=True,
                    stdout=True,
                    stderr=True,
                    timeout=settings.sandbox_timeout_seconds,
                )
                result = json.loads(output.decode().strip())
                return ExecutionResult(result.get("success", False), result.get("output"), result.get("error"))
            except Exception as e:
                log.error("sandbox.error", err=str(e))
                return ExecutionResult(False, None, str(e))

    async def _run_local(self, code: str, inputs: dict) -> ExecutionResult:
        """Fallback: execute locally."""
        try:
            exec_globals = {}
            exec(code, exec_globals)
            result = exec_globals.get("run")(inputs)
            return ExecutionResult(result.get("success", False), result.get("output"), result.get("error"))
        except Exception as e:
            return ExecutionResult(False, None, str(e))
