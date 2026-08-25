
import asyncio

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.agents.orchestrator import Orchestrator
from app.observability.trace import TraceRecorder
from app.memory.store import MemoryStore


async def run_once(question: str):
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    provider = OllamaProvider()
    orchestrator = Orchestrator(model=provider, tools=registry)

    async with get_session() as session:
        tracer = TraceRecorder(session)
        memory = MemoryStore(session)
        answer = await orchestrator.run(question, tracer=tracer, memory=memory)

    print(f"\nQ: {question}\nA: {answer}\nrun_id: {tracer.run_id}")


async def main():
    await init_db()
     
    await run_once("What is 25 times 4?")
    
    await run_once("I previously asked about 25 times 4 — what was double that result?")


asyncio.run(main())