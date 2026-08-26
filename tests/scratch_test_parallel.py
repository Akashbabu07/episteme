import asyncio
import time

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.agents.orchestrator import Orchestrator
from app.observability.trace import TraceRecorder
from app.memory.store import MemoryStore


async def main():
    await init_db()

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    provider = OllamaProvider()
    orchestrator = Orchestrator(model=provider, tools=registry)

    start = time.monotonic()

    async with get_session() as session:
        tracer = TraceRecorder(session)
        memory = MemoryStore(session)
        answer = await orchestrator.run(
            "What is 12 times 8, what is 100 divided by 4, and what is 9 plus 16?",
            tracer=tracer,
            memory=memory,
        )

    elapsed = time.monotonic() - start

    print("FINAL ANSWER:\n", answer)
    print(f"\nrun_id: {tracer.run_id}")
    print(f"Elapsed: {elapsed:.1f}s")


asyncio.run(main())