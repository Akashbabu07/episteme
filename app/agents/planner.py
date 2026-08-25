import json
from typing import Any

from pydantic import BaseModel, ValidationError

from app.models.base import Message, ModelInterface


class PlanTask(BaseModel):
    id: str
    description: str


class ResearchPlan(BaseModel):
    tasks: list[PlanTask]


PLANNER_SYSTEM_PROMPT = (
    "You are a research planner. Break the user's research question into "
    "2-5 concrete, independently-answerable sub-tasks. Each task should be "
    "something a researcher could investigate on its own using web search "
    "or calculation. Respond with ONLY a JSON object in this exact format, "
    "no other text:\n"
    '{"tasks": [{"id": "task_1", "description": "..."}, ...]}'
)


class Planner:
    def __init__(self, model: ModelInterface) -> None:
        self.model = model

    async def create_plan(self, question: str) -> ResearchPlan:
        response = await self.model.generate(
            messages=[
                Message(role="system", content=PLANNER_SYSTEM_PROMPT),
                Message(role="user", content=question),
            ],
        )

        raw = (response.content or "").strip()

      
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            data: dict[str, Any] = json.loads(raw)
            return ResearchPlan.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
           
            return ResearchPlan(
                tasks=[PlanTask(id="task_1", description=question)]
            )