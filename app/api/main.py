from fastapi import FastAPI
from pydantic import BaseModel

from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.web_search import WebSearchTool
from app.tools.fetch_page import FetchPageTool
from app.agents.research_agent import ResearchAgent
from app.observability.trace import TraceRecorder
from app.evidence.schemas import ResearchAnswer

app = FastAPI(title="Autonomous Research Lab", version="0.1.0")


class ResearchRequest(BaseModel):
    question: str


@app.on_event("startup")
async def startup() -> None:
    await init_db()


def build_agent() -> ResearchAgent:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(FetchPageTool())
    provider = OllamaProvider()
    return ResearchAgent(model=provider, tools=registry)


@app.post("/research", response_model=ResearchAnswer)
async def research(request: ResearchRequest) -> ResearchAnswer:
    agent = build_agent()

    async with get_session() as session:
        tracer = TraceRecorder(session)
        result = await agent.run(request.question, tracer=tracer)

    return ResearchAnswer(
        question=request.question,
        answer=result.final_answer or "No answer produced.",
        claims=[],
        run_id=str(tracer.run_id),
        stopped_reason=result.stopped_reason,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}