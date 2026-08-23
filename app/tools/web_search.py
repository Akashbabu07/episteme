from typing import Any

import httpx

from app.config.settings import get_settings
from app.tools.base import Tool, ToolResult


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web for current information. Returns a list of results "
        "with titles, URLs, and short snippets. Use this to find sources "
        "before making factual claims."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 10).",
            },
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.tavily_api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set in .env -- required for web_search tool."
            )
        self.api_key = settings.tavily_api_key

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = min(kwargs.get("max_results", 5), 10)

        if not query:
            return ToolResult(success=False, output=None, error="query is required")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "snippet": r.get("content"),
                }
                for r in data.get("results", [])
            ]
            return ToolResult(success=True, output=results)

        except httpx.TimeoutException:
            return ToolResult(success=False, output=None, error="Search request timed out")
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, output=None, error=f"Search API error: {e}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
