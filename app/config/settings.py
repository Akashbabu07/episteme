from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str


    model_provider: Literal["ollama", "groq", "anthropic"] = "ollama"


    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"


    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"


    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"


    tavily_api_key: str | None = None


    max_steps: int = 8
    max_tokens_per_run: int = 20000
    max_execution_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — loaded once per process."""
    return Settings()