import json
import re

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.failure_detector import FlaggedFailure
from app.models.base import Message, ModelInterface
from app.observability.models import StepRecord


class FailureAnalysis(BaseModel):
    root_cause: str
    improvement_recommendation: str


ANALYST_SYSTEM_PROMPT = (
    "You are a failure analyst for an AI research system. You are given: "
    "which quality dimension scored poorly, the numeric score, and the "
    "actual execution trace (what steps the system took). Identify the "
    "ROOT CAUSE — not just restating the symptom, but the specific "
    "mechanism that caused it (e.g. 'only one source was checked' rather "
    "than 'source quality was low'). Then give ONE concrete, specific "
    "improvement recommendation — a rule or process change, not vague "
    "advice like 'be more thorough'. Respond with ONLY this JSON:\n"
    '{"root_cause": "...", "improvement_recommendation": "..."}'
)


class RootCauseAnalyzer:
    def __init__(self, model: ModelInterface, session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def analyze(self, run_id, failure: FlaggedFailure) -> FailureAnalysis:
        result = await self.session.execute(
            select(StepRecord).where(StepRecord.run_id == run_id).order_by(StepRecord.created_at)
        )
        steps = list(result.scalars().all())

        # Bounded trace summary — per your spec's own memory-compression
        # principle, don't dump the entire raw trace into the prompt.
        trace_summary = "\n".join(
            f"- [{s.step_type}]" + (f" tool={s.tool_name}" if s.tool_name else "")
            + (f" ERROR: {s.error}" if s.error else "")
            for s in steps
        )

        analysis_input = (
            f"Failing dimension: {failure.dimension}\n"
            f"Score: {failure.score} (threshold: 0.6)\n\n"
            f"Execution trace summary:\n{trace_summary}"
        )

        response = await self.model.generate(
            messages=[
                Message(role="system", content=ANALYST_SYSTEM_PROMPT),
                Message(role="user", content=analysis_input),
            ],
        )

        raw = (response.content or "").strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()

        try:
            data = json.loads(raw)
            return FailureAnalysis.model_validate(data)
        except Exception:
            return FailureAnalysis(
                root_cause="Could not be determined — analyzer response was unparseable.",
                improvement_recommendation="Re-run analysis; consider a stronger model for this step.",
            )