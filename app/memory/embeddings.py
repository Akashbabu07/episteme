import ollama

from app.config.settings import get_settings


class EmbeddingClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = ollama.AsyncClient(host=settings.ollama_base_url)
        self.model = "nomic-embed-text"

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings(model=self.model, prompt=text)
        return response["embedding"]