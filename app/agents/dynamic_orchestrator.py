import asyncio
import uuid

from app.infrastructure.db import get_session
from app.agents.team_composer import TeamComposer
from app.agents.research_agent import ResearchAgent, AgentRunResult
from app.agents.roles import FACT_CHECKER_SYSTEM_PROMPT, CRITIC_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT
from app.models.base import Message, ModelInterface
from app.observability.trace import TraceRecorder
from app.tools.base import ToolRegistry


class SpecialistResult:
    def __init__(self, role_name: str, focus: str, result: AgentRunResult) -> None:
        self.role_name = role_name
        self.focus = focus
        self.result = result

    @property
    def succeeded(self) -> bool:
        return self.result.stopped_reason == "completed"


class DynamicOrchestrator:
    def __init__(self, model: ModelInterface, tools: ToolRegistry) -> None:
        self.model = model
        self.tools = tools
        self.composer = TeamComposer(model)

    async def run(self, question: str, tracer: TraceRecorder | None = None) -> str:
        if tracer:
            await tracer.start_run(question)

        # --- Stage 1: Compose the team ---
        team = await self.composer.compose_team(question)
        if tracer:
            await tracer.record_step(
                step_type="team_composition",
                input_data={"question": question},
                output_data={"roles": [r.model_dump() for r in team.roles]},
            )

        # --- Stage 2: Run each specialist in parallel ---
        run_id = tracer.run_id if tracer else uuid.uuid4()
        specialist_results = list(await asyncio.gather(
            *[self._run_specialist(role, question, run_id) for role in team.roles],
        ))
        findings_text = self._format_findings(specialist_results)

        # --- Stage 3: Fact-check + Critique (fixed, same as V4) ---
        fact_checker = ResearchAgent(
            model=self.model, tools=self.tools, system_prompt=FACT_CHECKER_SYSTEM_PROMPT
        )
        fc_result = await fact_checker.run(
            f"Findings to verify:\n{findings_text}", tracer=tracer, record_run=False
        )
        fact_check_notes = fc_result.final_answer or "No fact-check notes produced."
        if tracer:
            await tracer.record_step(
                step_type="fact_check", input_data={"findings": findings_text},
                output_data={"notes": fact_check_notes},
            )

        critic = ResearchAgent(
            model=self.model, tools=ToolRegistry(), system_prompt=CRITIC_SYSTEM_PROMPT
        )
        critique_result = await critic.run(
            f"Findings:\n{findings_text}\n\nFact-check notes:\n{fact_check_notes}",
            tracer=tracer, record_run=False,
        )
        critique_notes = critique_result.final_answer or "No critique produced."
        if tracer:
            await tracer.record_step(
                step_type="critique",
                input_data={"findings": findings_text, "fact_check": fact_check_notes},
                output_data={"critique": critique_notes},
            )

        # --- Stage 4: Synthesize ---
        final_answer = await self._synthesize(question, findings_text, fact_check_notes, critique_notes, team)

        if tracer:
            failed_count = sum(1 for s in specialist_results if not s.succeeded)
            await tracer.finish_run(
                status="completed", final_answer=final_answer,
                stopped_reason="completed" if failed_count == 0 else "completed_with_failures",
                total_input_tokens=0, total_output_tokens=0,
            )
        return final_answer

    async def _run_specialist(self, role, question: str, run_id: uuid.UUID) -> SpecialistResult:
        try:
            async with get_session() as isolated_session:
                isolated_tracer = TraceRecorder(isolated_session)
                isolated_tracer.run_id = run_id

                specialist = ResearchAgent(
                    model=self.model, tools=self.tools, system_prompt=role.system_prompt
                )
                task_prompt = f"Your focus area: {role.focus}\n\nOriginal question: {question}"
                result = await specialist.run(task_prompt, tracer=isolated_tracer, record_run=False)

            return SpecialistResult(role.role_name, role.focus, result)
        except Exception as e:
            failed_result = AgentRunResult(
                final_answer=None, messages=[], steps_taken=0,
                stopped_reason=f"error: {e}", total_input_tokens=0, total_output_tokens=0,
            )
            return SpecialistResult(role.role_name, role.focus, failed_result)

    def _format_findings(self, specialist_results: list[SpecialistResult]) -> str:
        lines = []
        for sr in specialist_results:
            status = "SUCCEEDED" if sr.succeeded else f"FAILED ({sr.result.stopped_reason})"
            answer = sr.result.final_answer or "No answer produced."
            lines.append(f"- Specialist: {sr.role_name} (focus: {sr.focus})\n  Status: {status}\n  Result: {answer}")
        return "\n".join(lines)

    async def _synthesize(
        self, question: str, findings: str, fact_check: str, critique: str, team
    ) -> str:
        team_summary = ", ".join(r.role_name for r in team.roles)
        synthesis_input = (
            f"Original question: {question}\n\n"
            f"Research team used: {team_summary}\n\n"
            f"Findings:\n{findings}\n\n"
            f"Fact-check notes:\n{fact_check}\n\n"
            f"Critique:\n{critique}"
        )
        response = await self.model.generate(
            messages=[
                Message(role="system", content=SYNTHESIZER_SYSTEM_PROMPT),
                Message(role="user", content=synthesis_input),
            ],
        )
        return response.content or "Unable to synthesize a final answer."