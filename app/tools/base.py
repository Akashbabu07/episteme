from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

class ToolResult(BaseModel):
    success: bool
    output: Any
    error: str | None = None



class Tool(ABC):
    """Every tool implements this. Tools are stateless — same input always
    goes through the same execute() path."""

    name: str
    description: str

    parameters: dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError

    def to_schema(self) -> dict[str, Any]:
        """Convert this tool into the schema format Ollama/OpenAI-style
        providers expect when listing available tools."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Holds all available tools, keyed by name. The agent loop will use
    this to (a) list tool schemas to send to the model and (b) look up
    and execute a tool the model chose to call."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]