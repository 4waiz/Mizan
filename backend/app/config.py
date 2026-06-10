"""Runtime configuration, env-driven. Safe defaults so the app runs with zero
setup. Policy knobs live here but the *rule logic* lives in policies/rules.py."""
from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MIZAN_",
        env_file=".env",
        extra="ignore",
    )

    # LLM
    # Accept the unprefixed LLM_PROVIDER / LLM_MODEL used in .env as well as the
    # MIZAN_-prefixed forms, so the existing env file "just works".
    llm_provider: str = Field(  # mock | anthropic | groq
        default="mock",
        validation_alias=AliasChoices("MIZAN_LLM_PROVIDER", "LLM_PROVIDER"),
    )
    llm_model: str = Field(
        default="claude-opus-4-8",
        validation_alias=AliasChoices("MIZAN_LLM_MODEL", "LLM_MODEL"),
    )
    # Accept both MIZAN_ANTHROPIC_API_KEY and the standard ANTHROPIC_API_KEY.
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MIZAN_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    )
    # Groq (live token-burning provider). Accept MIZAN_GROQ_API_KEY and GROQ_API_KEY.
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MIZAN_GROQ_API_KEY", "GROQ_API_KEY"),
    )
    groq_model: str = "llama-3.3-70b-versatile"

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
        """True only when a real provider is selected AND its key is present.
        Anything else falls back to the deterministic MockLLM."""
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.llm_provider == "groq":
            return bool(self.groq_api_key)
        return False

    @property
    def active_model(self) -> str:
        """The model name actually used for inference, per provider. Surfaced to
        the telemetry layer so the dashboard shows the true model in play."""
        if self.llm_provider == "groq":
            return self.groq_model
        if self.llm_provider == "anthropic":
            return self.llm_model
        return "mock-deterministic"


@lru_cache
def get_settings() -> Settings:
    # pydantic-settings reads the unprefixed ANTHROPIC_API_KEY / GROQ_API_KEY via
    # the field aliases above; we pull them explicitly as a belt-and-braces
    # fallback to keep the standard env names working.
    import os

    s = Settings()
    if not s.anthropic_api_key:
        s.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not s.groq_api_key:
        s.groq_api_key = os.getenv("GROQ_API_KEY")
    return s
