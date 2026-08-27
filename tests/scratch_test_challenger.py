import asyncio

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.web_search import WebSearchTool
from app.agents.orchestrator import Orchestrator
from app.observability.trace import TraceRecorder
from app.memory.store import MemoryStore


async def main():
    await init_db()

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())  # Challenger needs this to actually search
    provider = OllamaProvider()
    orchestrator = Orchestrator(model=provider, tools=registry)

    async with get_session() as session:
        tracer = TraceRecorder(session)
        memory = MemoryStore(session)
        answer = await orchestrator.run(
            "Does remote work increase productivity?",
            tracer=tracer,
            memory=memory,
        )

    print("FINAL ANSWER:\n", answer)
    print("\nrun_id:", tracer.run_id)


asyncio.run(main())