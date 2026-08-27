import asyncio

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.web_search import WebSearchTool
from app.agents.orchestrator import Orchestrator
from app.observability.trace import TraceRecorder
from app.memory.store import MemoryStore


QUESTIONS = [
    "What is 47 times 6?",                                    # expect: fast
    "What is the capital of France and its population?",       # expect: standard
    "Does remote work increase productivity?",                 # expect: rigorous
]


async def main():
    await init_db()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    provider = OllamaProvider()
    orchestrator = Orchestrator(model=provider, tools=registry)

    for question in QUESTIONS:
        async with get_session() as session:
            tracer = TraceRecorder(session)
            memory = MemoryStore(session)
            answer = await orchestrator.run(question, tracer=tracer, memory=memory)
        print(f"\nQ: {question}\nA: {answer[:200]}...\nrun_id: {tracer.run_id}")


asyncio.run(main())