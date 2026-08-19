from typing import Any

from app.tools.base import Tool, ToolResult

from typing import Any

from app.tools.base import Tool, ToolResult


class CalculatorTool(Tool):
    name = "calculator"
    description = (
        "Evaluate a basic arithmetic expression. "
        "Supports +, -, *, /, parentheses, and decimals. "
        "Example: '12 * (4 + 3)'"
    )
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression to evaluate, e.g. '12 * 4'",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        expression = kwargs.get("expression", "")

        allowed = set("0123456789+-*/(). ")
        if not expression or not set(expression).issubset(allowed):
            return ToolResult(
                success=False,
                output=None,
                error=f"Invalid or unsafe expression: {expression!r}",
            )

        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
