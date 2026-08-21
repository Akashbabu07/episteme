import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.models import RunRecord, StepRecord


class TraceRecorder:
    """Writes run/step records as the agent executes — not after the fact.
    If the process crashes mid-run, partial trace data is still on disk."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.run_id: uuid.UUID | None = None
        self._step_counter = 0

    async def start_run(self, question: str) -> uuid.UUID:
        run = RunRecord(question=question, status="running")
        self.session.add(run)
        await self.session.commit()
        self.run_id = run.id
        return run.id

    async def record_step(
        self,
        step_type: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        tool_name: str | None = None,
        latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        if self.run_id is None:
            raise RuntimeError("start_run() must be called before record_step()")

        self._step_counter += 1
        step = StepRecord(
            run_id=self.run_id,
            step_number=self._step_counter,
            step_type=step_type,
            input_data=input_data,
            output_data=output_data,
            tool_name=tool_name,
            latency_ms=latency_ms,
            error=error,
        )
        self.session.add(step)
        await self.session.commit()

    async def finish_run(
        self,
        status: str,
        final_answer: str | None,
        stopped_reason: str,
        total_input_tokens: int,
        total_output_tokens: int,
    ) -> None:
        from datetime import datetime, timezone

        run = await self.session.get(RunRecord, self.run_id)
        if run:
            run.status = status
            run.final_answer = final_answer
            run.stopped_reason = stopped_reason
            run.total_input_tokens = total_input_tokens
            run.total_output_tokens = total_output_tokens
            run.finished_at = datetime.now(timezone.utc)
            await self.session.commit()


@asynccontextmanager
async def timed_step():
    """Small helper to measure latency around a block of code."""
    start = time.monotonic()
    yield lambda: int((time.monotonic() - start) * 1000)