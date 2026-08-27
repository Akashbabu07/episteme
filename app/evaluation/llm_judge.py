import json
import re

from pydantic import BaseModel

from app.models.base import Message, ModelInterface


class LLMJudgeScores(BaseModel):
    factual_accuracy: float
    reasoning_quality: float
    justification: str


JUDGE_SYSTEM_PROMPT = (
    "You are an independent evaluator, not the agent that produced this "
    "research. You are given research findings and a final answer. Score "
    "two dimensions from 0.0 to 1.0:\n"
    "- factual_accuracy: does the final answer's claims match what the "
    "findings actually support? (not whether it sounds confident)\n"
    "- reasoning_quality: is the logic connecting findings to conclusion "
    "sound, or does it skip steps / overreach?\n"
    "Be critical — most answers have some flaw. A score of 1.0 should be "
    "rare. Respond with ONLY this JSON, no other text:\n"
    '{"factual_accuracy": 0.0, "reasoning_quality": 0.0, "justification": "..."}'
)


class LLMJudge:
    def __init__(self, model: ModelInterface) -> None:
        self.model = model

    async def evaluate(self, findings: str, final_answer: str) -> LLMJudgeScores:
        judge_input = f"Findings:\n{findings}\n\nFinal answer:\n{final_answer}"

        response = await self.model.generate(
            messages=[
                Message(role="system", content=JUDGE_SYSTEM_PROMPT),
                Message(role="user", content=judge_input),
            ],
        )

        raw = (response.content or "").strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()

        try:
            data = json.loads(raw)
            return LLMJudgeScores.model_validate(data)
        except Exception:
            # Same resilience pattern as the Planner in V2 — degrade, don't crash.
            return LLMJudgeScores(
                factual_accuracy=0.5,
                reasoning_quality=0.5,
                justification="Judge response could not be parsed; default neutral scores applied.",
            )