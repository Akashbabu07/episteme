import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.embeddings import EmbeddingClient
from app.memory.similarity import cosine_similarity
from app.observability.models import MemoryRecord


class MemoryStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.embedder = EmbeddingClient()

    async def store(self, run_id: uuid.UUID, memory_type: str, content: str) -> None:
        embedding = await self.embedder.embed(content)
        record = MemoryRecord(
            run_id=run_id,
            memory_type=memory_type,
            content=content,
            embedding=embedding,
        )
        self.session.add(record)
        await self.session.commit()

    async def retrieve_relevant(
        self, query: str, top_k: int = 3, min_similarity: float = 0.5
    ) -> list[str]:
        """Return up to top_k memory contents relevant to the query.
        Bounded on purpose — this is the 'don't dump everything' guardrail."""
        query_embedding = await self.embedder.embed(query)

        result = await self.session.execute(select(MemoryRecord))
        all_records = result.scalars().all()

        scored: list[tuple[float, str]] = []
        for record in all_records:
            score = cosine_similarity(query_embedding, record.embedding)
            if score >= min_similarity:
                scored.append((score, record.content))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:top_k]]