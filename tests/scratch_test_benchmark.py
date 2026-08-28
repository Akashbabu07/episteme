import asyncio

from app.infrastructure.db import init_db
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.web_search import WebSearchTool
from app.agents.strategy_selector import Strategy
from app.experiments.benchmark import BenchmarkRunner
from app.experiments.report import print_report


async def main():
    await init_db()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    provider = OllamaProvider()

    runner = BenchmarkRunner(model=provider, tools=registry)

   
    results = await runner.run_benchmark(strategies=[Strategy.FAST, Strategy.STANDARD])

    print_report(results)


asyncio.run(main())