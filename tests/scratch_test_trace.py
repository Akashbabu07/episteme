import asyncio

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.agents.research_agent import ResearchAgent
from app.observability.trace import TraceRecorder


async def main():
    await init_db()

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    provider = OllamaProvider()
    agent = ResearchAgent(model=provider, tools=registry)

    async with get_session() as session:
        tracer = TraceRecorder(session)
        result = await agent.run("What is 47 multiplied by 23, minus 100?", tracer=tracer)

    print(result)
    print(f"\nCheck Postgres — run_id: {tracer.run_id}")


asyncio.run(main())