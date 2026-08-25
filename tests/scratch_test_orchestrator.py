import asyncio

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.agents.orchestrator import Orchestrator
from app.observability.trace import TraceRecorder


async def main():
    await init_db()

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    provider = OllamaProvider()
    orchestrator = Orchestrator(model=provider, tools=registry)

    async with get_session() as session:
        tracer = TraceRecorder(session)
        answer = await orchestrator.run(
            "What is 12 times 8, and separately, what is 100 divided by 4?",
            tracer=tracer,
        )

    print("FINAL ANSWER:", answer)
    print("run_id:", tracer.run_id)


asyncio.run(main())