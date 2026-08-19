from abc import ABC, abstractmethod
from typing import Any, Literal


from pydantic import BaseModel


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]

class ModelResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = []
    finish_reason: Literal["stop", "tool_calls", "length", "error"]
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = {}

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None  # set when role == "tool"
    name: str | None = None

class ModelInterface(ABC):
    """Every LLM provider implements this. The agent loop only ever talks to this interface."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        """Send messages (+ optional tool schemas) to the provider, return a normalized response."""
        raise NotImplementedError