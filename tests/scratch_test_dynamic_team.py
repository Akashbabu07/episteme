import asyncio

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.web_search import WebSearchTool
from app.agents.dynamic_orchestrator import DynamicOrchestrator
from app.observability.trace import TraceRecorder


QUESTIONS = [
    "What is 8 times 9?",
    "Is quantum computing commercially viable?",
]


async def main():
    await init_db()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    provider = OllamaProvider()
    orchestrator = DynamicOrchestrator(model=provider, tools=registry)

    for question in QUESTIONS:
        async with get_session() as session:
            tracer = TraceRecorder(session)
            answer = await orchestrator.run(question, tracer=tracer)
        print(f"\nQ: {question}\nA: {answer[:300]}\nrun_id: {tracer.run_id}")


asyncio.run(main())