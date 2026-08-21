from typing import Literal
from pydantic import BaseModel


class Evidence(BaseModel):
    source_url: str
    title: str | None = None
    passage: str


class Claim(BaseModel):
    text: str
    confidence: Literal["verified", "weak", "uncertain"]
    evidence: list[Evidence] = []


class ResearchAnswer(BaseModel):
    question: str
    answer: str
    claims: list[Claim] = []
    run_id: str
    stopped_reason: str