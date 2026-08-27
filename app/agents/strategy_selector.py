import json
import re
from enum import Enum

from pydantic import BaseModel

from app.models.base import Message, ModelInterface


class Strategy(str, Enum):
    FAST = "fast"           # A: single agent, no plan, no verification stages
    STANDARD = "standard"   # B: plan + research + fact-check + critique
    RIGOROUS = "rigorous"   # C: full pipeline including challenger


class StrategyDecision(BaseModel):
    strategy: Strategy
    reasoning: str


SELECTOR_SYSTEM_PROMPT = (
    "You classify a research question into ONE of three strategies:\n"
    "- fast: simple factual/computational questions with one clear answer "
    "(e.g. arithmetic, single facts, definitions).\n"
    "- standard: questions needing a few distinct pieces of information "
    "combined, but with a fairly settled/uncontroversial answer.\n"
    "- rigorous: open-ended, debatable, or high-stakes questions where "
    "conclusions could be wrong, contested, or benefit from actively "
    "checking counter-evidence.\n"
    "Respond with ONLY this JSON:\n"
    '{"strategy": "fast|standard|rigorous", "reasoning": "..."}'
)


class StrategySelector:
    def __init__(self, model: ModelInterface) -> None:
        self.model = model

    async def select(self, question: str) -> StrategyDecision:
        response = await self.model.generate(
            messages=[
                Message(role="system", content=SELECTOR_SYSTEM_PROMPT),
                Message(role="user", content=question),
            ],
        )

        raw = (response.content or "").strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()

        try:
            data = json.loads(raw)
            return StrategyDecision.model_validate(data)
        except Exception:
            return StrategyDecision(
                strategy=Strategy.STANDARD,
                reasoning="Selector response unparseable; defaulted to standard strategy.",
            )