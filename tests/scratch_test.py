import asyncio
from app.models.ollama_provider import OllamaProvider
from app.models.base import Message

async def main():
    provider = OllamaProvider()
    response = await provider.generate(
        messages=[Message(role="user", content="Say hello in 5 words.")]
    )
    print(response)

asyncio.run(main())