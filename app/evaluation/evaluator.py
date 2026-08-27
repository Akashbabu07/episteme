from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.deterministic import evaluate_deterministic
from app.evaluation.llm_judge import LLMJudge
from app.models.base import ModelInterface
from app.observability.models import StepRecord, RunRecord, EvaluationRecord

WEIGHTS = {
    "completeness": 0.15,
    "tool_usage_efficiency": 0.10,
    "source_quality": 0.15,
    "contradiction_handling": 0.15,
    "factual_accuracy": 0.25,
    "reasoning_quality": 0.20,
}


class Evaluator:
    def __init__(self, model: ModelInterface, session: AsyncSession) -> None:
        self.judge = LLMJudge(model)
        self.session = session

    async def evaluate_run(
        self, run_id, task_count: int, task_success_count: int,
        max_steps_budget: int, findings: str,
    ) -> EvaluationRecord:
        result = await self.session.execute(
            select(StepRecord).where(StepRecord.run_id == run_id)
        )
        steps = list(result.scalars().all())

        run_result = await self.session.execute(
            select(RunRecord).where(RunRecord.id == run_id)
        )
        run = run_result.scalar_one()
        final_answer = run.final_answer or ""

        deterministic = evaluate_deterministic(
            steps=steps, task_count=task_count, task_success_count=task_success_count,
            max_steps_budget=max_steps_budget, final_answer=final_answer,
        )
        judge_scores = await self.judge.evaluate(findings, final_answer)

        overall = (
            deterministic.completeness * WEIGHTS["completeness"]
            + deterministic.tool_usage_efficiency * WEIGHTS["tool_usage_efficiency"]
            + deterministic.source_quality * WEIGHTS["source_quality"]
            + deterministic.contradiction_handling * WEIGHTS["contradiction_handling"]
            + judge_scores.factual_accuracy * WEIGHTS["factual_accuracy"]
            + judge_scores.reasoning_quality * WEIGHTS["reasoning_quality"]
        )

        record = EvaluationRecord(
            run_id=run_id,
            completeness=deterministic.completeness,
            tool_usage_efficiency=deterministic.tool_usage_efficiency,
            source_quality=deterministic.source_quality,
            contradiction_handling=deterministic.contradiction_handling,
            factual_accuracy=judge_scores.factual_accuracy,
            reasoning_quality=judge_scores.reasoning_quality,
            overall_score=round(overall, 3),
            notes={"deterministic_notes": deterministic.notes, "judge_justification": judge_scores.justification},
        )
        self.session.add(record)
        await self.session.commit()
        return record