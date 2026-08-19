import asyncio

from app.models.ollama_provider import OllamaProvider
from app.models.base import Message
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool


async def main():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    provider = OllamaProvider()
    response = await provider.generate(
        messages=[
            Message(
                role="user",
                content="What is 47 multiplied by 23? Use the calculator tool.",
            )
        ],
        tools=registry.schemas(),
    )

    print("finish_reason:", response.finish_reason)
    print("tool_calls:", response.tool_calls)
    print("content:", response.content)

    if response.tool_calls:
        call = response.tool_calls[0]
        tool = registry.get(call.name)
        if tool:
            result = await tool.execute(**call.arguments)
            print("tool result:", result)


asyncio.run(main())