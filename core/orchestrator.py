"""Main Orchestrator Agent."""
import uuid
import time
import structlog
from core.config import get_settings
from core.intent_parser import parse_intent
from core.router import route_request
from memory.episodic import EpisodicMemory
from memory.working import WorkingMemoryManager
from registry.search import ToolSearcher
from agents.generator import ToolGenerator
from agents.critic import ToolCritic
from agents.complexity_evaluator import ComplexityEvaluator
from agents.direct_llm_executor import DirectLLMExecutor
from agents.adapter import ToolAdapter
from execution.sandbox import SandboxExecutor
from execution.loader import ToolLoader
from registry.db import ToolRegistryDB
from registry.embedder import ToolEmbedder
from memory.session_manager import SessionManager
import traceback
log = structlog.get_logger()


class Orchestrator:
    def __init__(self):
        self.episodic = EpisodicMemory()
        self.working = WorkingMemoryManager()
        self.searcher = ToolSearcher()
        self.generator = ToolGenerator()
        self.critic = ToolCritic()
        self.complexity_evaluator = ComplexityEvaluator()
        self.direct_llm = DirectLLMExecutor()
        self.sandbox = SandboxExecutor()
        self.loader = ToolLoader()
        self.db = ToolRegistryDB()
        self.embedder = ToolEmbedder()
        self.sessions = SessionManager() 
        self.adapter = ToolAdapter()

    async def run(self, user_input: str, session_id: str = None) -> dict:
        """Execute user command."""
        session_id = session_id or str(uuid.uuid4())
        start = time.monotonic()

        log.info("orchestrator.run", session=session_id)
        session_id = session_id or str(uuid.uuid4())

        await self.sessions.create_session(session_id)
        try:
            # Parse intent
            intent = await parse_intent(user_input)
            log.info(
                "intent.after_parse",
                intent=intent
            )
            self.working.create(session_id, intent)

            # Evaluate task complexity
            complexity = await self.complexity_evaluator.evaluate(user_input, intent)
            log.info(
                "complexity.decision",
                complexity=complexity.get("complexity"),
                recommendation=complexity.get("recommendation"),
            )
            search_result = await self.searcher.find(
                intent.get("description", "")
                )

            if (
                search_result
                and search_result.similarity_score >= 0.65
                ):
                    log.info(
                    "tool_found_skip_direct_llm",
                    tool=search_result.tool.name,
                    similarity=search_result.similarity_score
                )
            else:
                
            
            # Direct LLM path for simple tasks
                if complexity.get("recommendation") == "direct_llm":
                    log.info("orchestrator.direct_llm_path")
                    result = await self.direct_llm.execute(user_input, intent)

                    runtime_ms = int((time.monotonic() - start) * 1000)
                    session_id = session_id or str(uuid.uuid4())

                    await self.episodic.create_session(session_id)
                    await self.episodic.store(
                        session_id=session_id,
                        user_input=user_input,
                        tool_id=None,
                        execution_mode="direct_llm",
                        tool_result=result.get("output"),
                        match_type="direct_llm",
                        similarity_score=0.0,
                        runtime_ms=runtime_ms,
                        success=result.get("success", False),
                    )

                return {
                    "session_id": session_id,
                    "result": result.get("output"),
                    "tool_id":'None',
                    'execution_mode':"direct_llm",
                    "tool_version": "n/a",
                    "match_type": "direct_llm",
                    "complexity": complexity.get("complexity"),
                    "reasoning": complexity.get("reasoning"),
                    "runtime_ms": runtime_ms,
                    "success": result.get("success", False),
                }

            # Tool-based path for complex tasks
            # Search for similar tools
            search_result = await self.searcher.find(intent.get("description", ""))
            settings = get_settings()
            route = route_request(search_result, settings)

            log.info("router.decision", route=route.match_type, score=route.similarity_score)

          # Get or build tool
            tool = None
            code = None

            if route.match_type == "reuse" and search_result:
                log.info("orchestrator.reusing_tool")

                tool = search_result.tool
                code = self.loader.load(tool)

            elif route.match_type == "adapt" and search_result:
                log.info("orchestrator.adapting_tool")

                tool = search_result.tool

                adapted_tool, code = await self.adapter.adapt(
                existing_tool=tool,
                new_intent=intent
            )

            else:
                log.info("orchestrator.generating_tool")

                code, tool_meta = await self.generator.generate(intent)

                critique = await self.critic.validate(code, tool_meta)
                log.info(
                    "critic.result",
                    passed=critique.passed,
                    reliability_score=critique.reliability_score
                )
                if critique.passed:
                    tool = await self.db.create(
                    tool_meta,
                    critique.reliability_score
                )
                else:
                    log.error(
                    "critic.failed",
                    issues=critique.issues
                    )

                    return {
                        "session_id": session_id,
                        "error": "Tool validation failed",
                        "issues": critique.issues,
                        "success": False,
                    }


                self.loader.save(tool, code)

                embedding = self.embedder.embed(tool.description)

                await self.searcher.add(
                    tool.id,
                    embedding
                 )
            tool_inputs = intent.get("inputs", {})
            log.info(
                "tool.inputs.debug",
                inputs=tool_inputs,
                input_types={
                    k: type(v).__name__
                    for k, v in tool_inputs.items()
                    }
            )

            log.info(
                "tool.execution.start",
                tool=tool.name,
                inputs=intent.get("inputs", {})
            )
            
            # has_real_data = any(
            #     not isinstance(v, dict)
            #     for v in tool_inputs.values()
            #     )

            # if not has_real_data:
            #     return {
            #     "session_id": session_id,
            #     "tool_id": tool.id,
            #     "message": "Tool created successfully",
            #     "success": True
            #     }
            result = await self.sandbox.run(
                    code,
                    tool,
                    tool_inputs
                    )

            log.info(
                    "tool.execution.end",
                    success=result.success,
                    output=result.output,
                    error=result.error
                )
            # Persist
            runtime_ms = int((time.monotonic() - start) * 1000)
            await self.db.increment_usage(tool.id, success=result.success)
            await self.episodic.store(
                session_id=session_id,
                user_input=user_input,
                tool_id=tool.id,
                execution_mode=route.match_type,
                tool_result=result.output,
                match_type=route.match_type,
                similarity_score=route.similarity_score,
                runtime_ms=runtime_ms,
                success=result.success,
            )

            log.info("orchestrator.done", runtime_ms=runtime_ms, success=result.success)

            return {
                "session_id": session_id,
                "result": result.output,
                'tool_id':tool.id,
                "execution_mode" :route.match_type,
                "tool_version": tool.version,
                "match_type": route.match_type,
                "complexity": complexity.get("complexity"),
                "runtime_ms": runtime_ms,
                "success": result.success,
            }

        except Exception as e:
            runtime_ms = int((time.monotonic() - start) * 1000)
             
            log.error(
                    "orchestrator.error",
                    err=str(e),
                    traceback=traceback.format_exc()
                )
