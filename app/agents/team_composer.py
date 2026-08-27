import json
import re

from pydantic import BaseModel

from app.models.base import Message, ModelInterface


class SpecialistRole(BaseModel):
    role_name: str          # e.g. "Quantum Researcher"
    focus: str               # what this specialist should investigate
    system_prompt: str       # the actual instructions this agent will run with


class ResearchTeam(BaseModel):
    roles: list[SpecialistRole]


COMPOSER_SYSTEM_PROMPT = (
    "You design a research team for a given question. Decide 1-4 "
    "specialist roles genuinely needed to investigate it well — do not "
    "create roles just to have more of them. Each role needs a name, a "
    "specific focus area, and a one-paragraph system prompt instructing "
    "that specialist how to approach their part of the research (they "
    "will have access to web_search and calculator tools). For a simple "
    "question, one generalist role may be entirely appropriate. Respond "
    "with ONLY this JSON:\n"
    '{"roles": [{"role_name": "...", "focus": "...", "system_prompt": "..."}]}'
)


class TeamComposer:
    def __init__(self, model: ModelInterface) -> None:
        self.model = model

    async def compose_team(self, question: str) -> ResearchTeam:
        response = await self.model.generate(
            messages=[
                Message(role="system", content=COMPOSER_SYSTEM_PROMPT),
                Message(role="user", content=question),
            ],
        )

        raw = (response.content or "").strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()

        try:
            data = json.loads(raw)
            team = ResearchTeam.model_validate(data)
            if not team.roles:
                raise ValueError("empty team")
            return team
        except Exception:
            # Fallback: one generalist researcher — same resilience pattern
            # as the Planner (V2) and StrategySelector (V9).
            from app.agents.roles import RESEARCHER_SYSTEM_PROMPT
            return ResearchTeam(
                roles=[
                    SpecialistRole(
                        role_name="Generalist Researcher",
                        focus=question,
                        system_prompt=RESEARCHER_SYSTEM_PROMPT,
                    )
                ]
            )