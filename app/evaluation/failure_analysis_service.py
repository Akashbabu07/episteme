from app.evaluation.failure_detector import detect_failures
from app.evaluation.root_cause import RootCauseAnalyzer
from app.models.base import ModelInterface
from app.observability.models import EvaluationRecord, FailureAnalysisRecord
from sqlalchemy.ext.asyncio import AsyncSession


class FailureAnalysisService:
    def __init__(self, model: ModelInterface, session: AsyncSession) -> None:
        self.analyzer = RootCauseAnalyzer(model, session)
        self.session = session

    async def analyze_run(self, evaluation: EvaluationRecord) -> list[FailureAnalysisRecord]:
        failures = detect_failures(evaluation)

        if not failures:
            return []  # nothing flagged — no analysis needed, and that's a fine outcome

        records = []
        for failure in failures:
            analysis = await self.analyzer.analyze(evaluation.run_id, failure)

            record = FailureAnalysisRecord(
                run_id=evaluation.run_id,
                evaluation_id=evaluation.id,
                flagged_dimensions={failure.dimension: failure.score},
                root_cause=analysis.root_cause,
                improvement_recommendation=analysis.improvement_recommendation,
            )
            self.session.add(record)
            records.append(record)

        await self.session.commit()
        return records