import time

from app.config.settings import get_settings
from app.models.base import Message, ModelInterface
from app.tools.base import ToolRegistry
from app.observability.trace import TraceRecorder


class AgentRunResult:
    def __init__(
        self,
        final_answer: str | None,
        messages: list[Message],
        steps_taken: int,
        stopped_reason: str,
        total_input_tokens: int,
        total_output_tokens: int,
    ) -> None:
        self.final_answer = final_answer
        self.messages = messages
        self.steps_taken = steps_taken
        self.stopped_reason = stopped_reason
        self.total_input_tokens = total_input_tokens
        self.total_output_tokens = total_output_tokens

    def __repr__(self) -> str:
        return (
            f"AgentRunResult(stopped_reason={self.stopped_reason!r}, "
            f"steps={self.steps_taken}, "
            f"final_answer={self.final_answer!r})"
        )


SYSTEM_PROMPT = (
    "You are a research agent. Answer the user's question as accurately as "
    "possible. Use the available tools when they would help you produce a "
    "more accurate answer. When you have enough information, give a clear, "
    "direct final answer in plain text — do not call a tool if you already "
    "have everything you need."
)


class ResearchAgent:
    def __init__(self, model: ModelInterface, tools: ToolRegistry) -> None:
        self.model = model
        self.tools = tools
        self.settings = get_settings()

    async def run(
        self,
        question: str,
        tracer: TraceRecorder | None = None,
    ) -> AgentRunResult:

        # Start tracing this run
        if tracer:
            await tracer.start_run(question)

        messages: list[Message] = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=question),
        ]

        total_input_tokens = 0
        total_output_tokens = 0
        start_time = time.monotonic()

        for step in range(1, self.settings.max_steps + 1):

            # Check execution time limit
            elapsed = time.monotonic() - start_time

            if elapsed > self.settings.max_execution_seconds:
                if tracer:
                    await tracer.finish_run(
                        "stopped",
                        None,
                        "time_budget_exceeded",
                        total_input_tokens,
                        total_output_tokens,
                    )

                return AgentRunResult(
                    final_answer=None,
                    messages=messages,
                    steps_taken=step - 1,
                    stopped_reason="time_budget_exceeded",
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                )

            # Check token limit
            if (
                total_input_tokens + total_output_tokens
                > self.settings.max_tokens_per_run
            ):
                if tracer:
                    await tracer.finish_run(
                        "stopped",
                        None,
                        "token_budget_exceeded",
                        total_input_tokens,
                        total_output_tokens,
                    )

                return AgentRunResult(
                    final_answer=None,
                    messages=messages,
                    steps_taken=step - 1,
                    stopped_reason="token_budget_exceeded",
                    total_input_tokens=total_input_tokens,
                    total_output_tokens=total_output_tokens,
                )



            step_start = time.monotonic()

            response = await self.model.generate(
                messages=messages,
                tools=self.tools.schemas(),
            )

            latency_ms = int(
                (time.monotonic() - step_start) * 1000
            )

            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens

            # Record model call
            if tracer:
                await tracer.record_step(
                    step_type="model_call",
                    input_data={
                        "messages": [
                            message.model_dump()
                            for message in messages
                        ]
                    },
                    output_data={
                        "content": response.content,
                        "tool_calls": [
                            tool_call.model_dump()
                            for tool_call in response.tool_calls
                        ],
                    },
                    latency_ms=latency_ms,
                )



            if response.tool_calls:

                messages.append(
                    Message(
                        role="assistant",
                        content=response.content or "",
                    )
                )

                for call in response.tool_calls:

                    tool = self.tools.get(call.name)
                    tool_error = None

                    tool_start = time.monotonic()

                    if tool is None:
                        tool_output = (
                            f"Error: unknown tool '{call.name}'"
                        )
                        tool_error = tool_output

                    else:
                        try:
                            result = await tool.execute(
                                **call.arguments
                            )

                            tool_output = (
                                str(result.output)
                                if result.success
                                else f"Error: {result.error}"
                            )

                            tool_error = result.error

                        except Exception as e:
                            tool_output = (
                                f"Error executing tool: {e}"
                            )
                            tool_error = str(e)

                    tool_latency_ms = int(
                        (time.monotonic() - tool_start) * 1000
                    )


                    if tracer:
                        await tracer.record_step(
                            step_type="tool_call",
                            input_data={
                                "tool": call.name,
                                "arguments": call.arguments,
                            },
                            output_data={
                                "result": tool_output,
                            },
                            tool_name=call.name,
                            latency_ms=tool_latency_ms,
                            error=tool_error,
                        )

                    messages.append(
                        Message(
                            role="tool",
                            content=tool_output,
                            tool_call_id=call.id,
                            name=call.name,
                        )
                    )

                continue



            if tracer:
                await tracer.finish_run(
                    "completed",
                    response.content,
                    "completed",
                    total_input_tokens,
                    total_output_tokens,
                )

            return AgentRunResult(
                final_answer=response.content,
                messages=messages,
                steps_taken=step,
                stopped_reason="completed",
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
            )



        if tracer:
            await tracer.finish_run(
                "stopped",
                None,
                "max_steps_exceeded",
                total_input_tokens,
                total_output_tokens,
            )

        return AgentRunResult(
            final_answer=None,
            messages=messages,
            steps_taken=self.settings.max_steps,
            stopped_reason="max_steps_exceeded",
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
        )