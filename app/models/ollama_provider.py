from typing import Any

import ollama

from app.config.settings import get_settings
from app.models.base import Message, ModelInterface, ModelResponse, ToolCall


class OllamaProvider(ModelInterface):
    def __init__(self) -> None:
        settings = get_settings()
        self.client = ollama.AsyncClient(host=settings.ollama_base_url)
        self.model = settings.ollama_model

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        ollama_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        response = await self.client.chat(
            model=self.model,
            messages=ollama_messages,
            tools=tools or [],
        )

        message = response["message"]
        tool_calls = []
        if message.get("tool_calls"):
            for i, tc in enumerate(message["tool_calls"]):
                tool_calls.append(
                    ToolCall(
                        id=f"call_{i}",
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    )
                )

        finish_reason = "tool_calls" if tool_calls else "stop"

        return ModelResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            input_tokens=response.get("prompt_eval_count", 0),
            output_tokens=response.get("eval_count", 0),
            raw=response,
        )