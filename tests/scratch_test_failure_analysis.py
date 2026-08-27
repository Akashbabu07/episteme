import asyncio
import uuid

from app.infrastructure.db import get_session
from app.models.ollama_provider import OllamaProvider
from app.evaluation.failure_analysis_service import FailureAnalysisService
from app.observability.models import EvaluationRecord
from sqlalchemy import select


EVALUATION_RUN_ID = uuid.UUID("PASTE_THE_RUN_ID_YOU_EVALUATED_IN_V7_HERE")


async def main():
    provider = OllamaProvider()

    async with get_session() as session:
        result = await session.execute(
            select(EvaluationRecord).where(EvaluationRecord.run_id == EVALUATION_RUN_ID)
        )
        evaluation = result.scalar_one()

        service = FailureAnalysisService(model=provider, session=session)
        analyses = await service.analyze_run(evaluation)

    if not analyses:
        print("No failures flagged — all dimensions scored above threshold.")
    for a in analyses:
        print(f"\n--- Flagged: {a.flagged_dimensions} ---")
        print("Root cause:", a.root_cause)
        print("Recommendation:", a.improvement_recommendation)


asyncio.run(main())