"""Application configuration, loaded from environment variables (prefix ``SA_``)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SA_", env_file=".env", extra="ignore")

    environment: str = "local"
    confidence_review_threshold: float = 0.80
    balance_tolerance: float = 0.01
    memo_mode: str = "template"  # template | llm
    llm_providers: str = "anthropic,openai,gemini,deepseek,ollama"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
