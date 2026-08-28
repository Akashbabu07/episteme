from fastapi import FastAPI
from pydantic import BaseModel
from app.agents.orchestrator import Orchestrator
from app.infrastructure.db import init_db, get_session
from app.models.ollama_provider import OllamaProvider
from app.tools.base import ToolRegistry
from fastapi.middleware.cors import CORSMiddleware
from app.tools.calculator import CalculatorTool
from app.tools.web_search import WebSearchTool
from app.tools.fetch_page import FetchPageTool
from app.agents.research_agent import ResearchAgent
from app.observability.trace import TraceRecorder
from app.evidence.schemas import ResearchAnswer
from app.memory.store import MemoryStore
app = FastAPI(title="Autonomous Research Lab", version="0.1.0")


class ResearchRequest(BaseModel):
    question: str


@app.on_event("startup")
async def startup() -> None:
    await init_db()

def build_agent() -> Orchestrator:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(FetchPageTool())
    provider = OllamaProvider()
    return Orchestrator(model=provider, tools=registry)


@app.post("/research", response_model=ResearchAnswer)
async def research(request: ResearchRequest) -> ResearchAnswer:
    orchestrator = build_agent()

    async with get_session() as session:
        tracer = TraceRecorder(session)
        memory = MemoryStore(session)
        final_answer = await orchestrator.run(request.question, tracer=tracer, memory=memory)

    return ResearchAnswer(
        question=request.question,
        answer=final_answer,
        claims=[],
        run_id=str(tracer.run_id),
        stopped_reason="completed",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}