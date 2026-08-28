import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import Orchestrator
from app.agents.strategy_selector import Strategy
from app.evaluation.evaluator import Evaluator
from app.infrastructure.db import get_session
from app.memory.store import MemoryStore
from app.models.base import ModelInterface
from app.observability.trace import TraceRecorder
from app.tools.base import ToolRegistry


@dataclass
class BenchmarkQuestion:
    question: str
    task_count_hint: int  # rough expected task count, for evaluator's completeness scoring


@dataclass
class BenchmarkResult:
    question: str
    strategy: str
    run_id: uuid.UUID
    final_answer: str
    overall_score: float | None
    error: str | None = None


DEFAULT_BENCHMARK: list[BenchmarkQuestion] = [
    BenchmarkQuestion("What is 47 times 23?", task_count_hint=1),
    BenchmarkQuestion("What is the capital of Japan and its approximate population?", task_count_hint=2),
    BenchmarkQuestion("Does remote work increase productivity?", task_count_hint=3),
]


class BenchmarkRunner:
    def __init__(self, model: ModelInterface, tools: ToolRegistry) -> None:
        self.model = model
        self.tools = tools

    async def run_benchmark(
        self,
        strategies: list[Strategy],
        questions: list[BenchmarkQuestion] = DEFAULT_BENCHMARK,
    ) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []

        for bq in questions:
            for strategy in strategies:
                result = await self._run_one(bq, strategy)
                results.append(result)

        return results

    async def _run_one(self, bq: BenchmarkQuestion, strategy: Strategy) -> BenchmarkResult:
        orchestrator = Orchestrator(model=self.model, tools=self.tools)

        try:
            async with get_session() as session:
                tracer = TraceRecorder(session)
                memory = MemoryStore(session)
                final_answer = await orchestrator.run(
                    bq.question, tracer=tracer, memory=memory, force_strategy=strategy
                )
                run_id = tracer.run_id

            overall_score = await self._evaluate(run_id, bq)

            return BenchmarkResult(
                question=bq.question, strategy=strategy.value, run_id=run_id,
                final_answer=final_answer, overall_score=overall_score,
            )
        except Exception as e:
            return BenchmarkResult(
                question=bq.question, strategy=strategy.value, run_id=uuid.uuid4(),
                final_answer="", overall_score=None, error=str(e),
            )

    async def _evaluate(self, run_id: uuid.UUID, bq: BenchmarkQuestion) -> float | None:
        try:
            async with get_session() as session:
                evaluator = Evaluator(model=self.model, session=session)
                record = await evaluator.evaluate_run(
                    run_id=run_id,
                    task_count=bq.task_count_hint,
                    task_success_count=bq.task_count_hint,  # optimistic default; refine if you track real failures
                    max_steps_budget=8,
                    findings=bq.question,  # simplified — a fuller version would pull real findings from steps
                )
                return record.overall_score
        except Exception:
            return None  # evaluation failing shouldn't crash the whole benchmark