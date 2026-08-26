import asyncio
import uuid

from app.infrastructure.db import get_session
from app.agents.planner import Planner, ResearchPlan
from app.agents.research_agent import ResearchAgent, AgentRunResult
from app.agents.roles import (
    FACT_CHECKER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
)
from app.models.base import Message, ModelInterface
from app.memory.store import MemoryStore
from app.observability.trace import TraceRecorder
from app.tools.base import ToolRegistry


class TaskResult:
    def __init__(self, task_id: str, description: str, result: AgentRunResult) -> None:
        self.task_id = task_id
        self.description = description
        self.result = result

    @property
    def succeeded(self) -> bool:
        return self.result.stopped_reason == "completed"


class Orchestrator:
    def __init__(self, model: ModelInterface, tools: ToolRegistry) -> None:
        self.model = model
        self.tools = tools
        self.planner = Planner(model)

    async def run(
        self,
        question: str,
        tracer: TraceRecorder | None = None,
        memory: MemoryStore | None = None,
    ) -> str:
        if tracer:
            await tracer.start_run(question)

        # --- Stage 1: Plan ---
        plan = await self.planner.create_plan(question)
        if tracer:
            await tracer.record_step(
                step_type="plan",
                input_data={"question": question},
                output_data={"tasks": [t.model_dump() for t in plan.tasks]},
            )

        # --- Stage 2: Research (PARALLEL — one Researcher per task) ---
        run_id = tracer.run_id if tracer else uuid.uuid4()
        task_results = await asyncio.gather(
            *[self._run_task_isolated(task, run_id, memory) for task in plan.tasks],
            return_exceptions=False,  # _run_task_isolated already catches internally
        )
        task_results = list(task_results)

        findings_text = self._format_findings(task_results)

        # --- Stage 3: Fact Check ---
        fact_checker = ResearchAgent(
            model=self.model, tools=self.tools, system_prompt=FACT_CHECKER_SYSTEM_PROMPT
        )
        fact_check_result = await fact_checker.run(
            f"Findings to verify:\n{findings_text}", tracer=tracer, record_run=False
        )
        fact_check_notes = fact_check_result.final_answer or "No fact-check notes produced."
        if tracer:
            await tracer.record_step(
                step_type="fact_check",
                input_data={"findings": findings_text},
                output_data={"notes": fact_check_notes},
            )

        # --- Stage 4: Critique (no tools — pure reasoning over text) ---
        empty_tools = ToolRegistry()
        critic = ResearchAgent(
            model=self.model, tools=empty_tools, system_prompt=CRITIC_SYSTEM_PROMPT
        )
        critique_result = await critic.run(
            f"Findings:\n{findings_text}\n\nFact-check notes:\n{fact_check_notes}",
            tracer=tracer,
            record_run=False,
        )
        critique_notes = critique_result.final_answer or "No critique produced."
        if tracer:
            await tracer.record_step(
                step_type="critique",
                input_data={"findings": findings_text, "fact_check": fact_check_notes},
                output_data={"critique": critique_notes},
            )

        # --- Stage 5: Synthesize ---
        final_answer = await self._synthesize(question, findings_text, fact_check_notes, critique_notes)

        if tracer:
            failed_count = sum(1 for t in task_results if not t.succeeded)
            await tracer.finish_run(
                status="completed",
                final_answer=final_answer,
                stopped_reason="completed" if failed_count == 0 else "completed_with_failures",
                total_input_tokens=0,
                total_output_tokens=0,
            )

        return final_answer

    async def _run_task_isolated(
        self,
        task,
        run_id: uuid.UUID,
        memory: MemoryStore | None,
    ) -> TaskResult:
        """Runs one research task with its own DB session — required for
        safe concurrent writes. Never raises; failures are captured in the
        result so one bad task can't take down the whole gather()."""

        task_prompt = task.description
        try:
            if memory:
                relevant = await memory.retrieve_relevant(task.description)
                if relevant:
                    context = "\n".join(f"- {r}" for r in relevant)
                    task_prompt = f"{task.description}\n\nRelevant prior findings:\n{context}"

            async with get_session() as isolated_session:
                isolated_tracer = TraceRecorder(isolated_session)
                isolated_tracer.run_id = run_id  # attach to the SAME run, don't start a new one

                researcher = ResearchAgent(model=self.model, tools=self.tools)
                result = await researcher.run(task_prompt, tracer=isolated_tracer, record_run=False)

            if memory and result.final_answer:
                # Memory writes use their own session too, for the same reason
                async with get_session() as mem_session:
                    mem_store = MemoryStore(mem_session)
                    await mem_store.store(
                        run_id=run_id,
                        memory_type="research_finding",
                        content=f"{task.description} → {result.final_answer}",
                    )

            return TaskResult(task.id, task.description, result)

        except Exception as e:
            failed_result = AgentRunResult(
                final_answer=None,
                messages=[],
                steps_taken=0,
                stopped_reason=f"error: {e}",
                total_input_tokens=0,
                total_output_tokens=0,
            )
            return TaskResult(task.id, task.description, failed_result)

    def _format_findings(self, task_results: list[TaskResult]) -> str:
        lines = []
        for tr in task_results:
            status = "SUCCEEDED" if tr.succeeded else f"FAILED ({tr.result.stopped_reason})"
            answer = tr.result.final_answer or "No answer produced."
            lines.append(f"- Task: {tr.description}\n  Status: {status}\n  Result: {answer}")
        return "\n".join(lines)

    async def _synthesize(
        self, question: str, findings: str, fact_check: str, critique: str
    ) -> str:
        synthesis_input = (
            f"Original question: {question}\n\n"
            f"Research findings:\n{findings}\n\n"
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