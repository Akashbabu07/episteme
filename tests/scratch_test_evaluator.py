import asyncio
import uuid

from app.infrastructure.db import get_session
from app.models.ollama_provider import OllamaProvider
from app.evaluation.evaluator import Evaluator


RUN_ID = uuid.UUID("PASTE_A_REAL_RUN_ID_HERE")


async def main():
    provider = OllamaProvider()

    async with get_session() as session:
        evaluator = Evaluator(model=provider, session=session)
        record = await evaluator.evaluate_run(
            run_id=RUN_ID,
            task_count=3,            
            task_success_count=3,
            max_steps_budget=8,
            findings="(paste the findings text or re-fetch from steps if you want it exact)",
        )

    print("Overall score:", record.overall_score)
    print("Completeness:", record.completeness)
    print("Tool usage efficiency:", record.tool_usage_efficiency)
    print("Source quality:", record.source_quality)
    print("Contradiction handling:", record.contradiction_handling)
    print("Factual accuracy:", record.factual_accuracy)
    print("Reasoning quality:", record.reasoning_quality)
    print("Notes:", record.notes)


asyncio.run(main())