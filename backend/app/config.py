from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./thinkmate_dev.db"
    # Primary model provider: Google Gemini (free tier via Google AI Studio),
    # called through its OpenAI-compatible endpoint. Poe is the alternate used
    # when Gemini is unavailable/busy. Leave gemini_api_key blank to use Poe only.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    hf_api_token: str = ""
    hf_model: str = "google/gemma-2-2b-it"
    poe_api_key: str = ""
    poe_model: str = "GLM-5"
    poe_base_url: str = "https://api.poe.com/v1"
    admin_password: str = "change-me"
    app_env: str = "development"
    consent_version: str = "v1-2026-06-19"
    seed_demo_students: bool = True
    pilot_access_codes: str = ""
    cors_origins: str = "*"
    admin_rate_limit_per_minute: int = 30
    # Sign-in spam guard. Per-IP; keep generous because a whole lab class can sit
    # behind one campus NAT and sign in within the same minute.
    auth_rate_limit_per_minute: int = 30
    # Crossover integrity: Activity 2 cannot start before Activity 1 is complete
    # (the randomised A/B sequence is defined by task order, so free ordering
    # would silently swap a student's assigned condition sequence).
    enforce_task_order: bool = True
    # Soft ceiling on tutor exchanges per session; past it the tutor closes with
    # a canned wrap-up instead of another (paid) model call.
    max_exchanges: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
