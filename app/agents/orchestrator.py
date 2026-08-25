from app.agents.planner import Planner, ResearchPlan
from app.agents.research_agent import ResearchAgent, AgentRunResult
from app.models.base import Message, ModelInterface
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


SYNTHESIS_SYSTEM_PROMPT = (
    "You are a research synthesizer. You are given a research question and "
    "the results of several sub-tasks investigating it. Combine them into "
    "one clear, direct final answer. If any sub-task failed or produced no "
    "useful result, acknowledge the gap honestly rather than ignoring it — "
    "do not present uncertain conclusions as settled facts."
)


class Orchestrator:
    def __init__(self, model: ModelInterface, tools: ToolRegistry) -> None:
        self.model = model
        self.tools = tools
        self.planner = Planner(model)

    async def run(self, question: str, tracer: TraceRecorder | None = None) -> str:
        if tracer:
            await tracer.start_run(question)

        plan = await self.planner.create_plan(question)

        if tracer:
            await tracer.record_step(
                step_type="plan",
                input_data={"question": question},
                output_data={"tasks": [t.model_dump() for t in plan.tasks]},
            )

        task_results: list[TaskResult] = []
        for task in plan.tasks:
            executor = ResearchAgent(model=self.model, tools=self.tools)
            result = await executor.run(task.description, tracer=tracer)
            task_results.append(TaskResult(task.id, task.description, result))

        final_answer = await self._synthesize(question, task_results)

        if tracer:
            failed_count = sum(1 for t in task_results if not t.succeeded)
            await tracer.finish_run(
                status="completed",
                final_answer=final_answer,
                stopped_reason="completed" if failed_count == 0 else "completed_with_failures",
                total_input_tokens=0,  # aggregated per-task already recorded individually
                total_output_tokens=0,
            )

        return final_answer

    async def _synthesize(self, question: str, task_results: list[TaskResult]) -> str:
        summary_lines = []
        for tr in task_results:
            status = "SUCCEEDED" if tr.succeeded else f"FAILED ({tr.result.stopped_reason})"
            answer = tr.result.final_answer or "No answer produced."
            summary_lines.append(f"- Task: {tr.description}\n  Status: {status}\n  Result: {answer}")

        synthesis_input = (
            f"Original question: {question}\n\n"
            f"Sub-task results:\n" + "\n".join(summary_lines)
        )

        response = await self.model.generate(
            messages=[
                Message(role="system", content=SYNTHESIS_SYSTEM_PROMPT),
                Message(role="user", content=synthesis_input),
            ],
        )
        return response.content or "Unable to synthesize a final answer."