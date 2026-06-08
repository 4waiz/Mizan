"""Runtime configuration, env-driven. Safe defaults so the app runs with zero
setup. Policy knobs live here but the *rule logic* lives in policies/rules.py."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MIZAN_",
        env_file=".env",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "mock"          # mock | anthropic
    llm_model: str = "claude-opus-4-8"
    anthropic_api_key: str | None = None

    # Database
    database_url: str = "sqlite:///./mizan.db"

    # Policy knobs (Sheikh Zayed Housing Programme)
    max_deduction_ratio: float = 0.20
    sla_working_days: int = 5

    # Confidence routing
    auto_approve_confidence: float = 0.75

    # Frontend convenience
    api_base_url: str = "http://localhost:8000"

    @property
    def use_real_llm(self) -> bool:
        return self.llm_provider == "anthropic" and bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    # pydantic-settings also reads ANTHROPIC_API_KEY (no prefix) via the field
    # alias below; we pull it explicitly to keep the standard env name working.
    import os

    s = Settings()
    if not s.anthropic_api_key:
        s.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    return s
