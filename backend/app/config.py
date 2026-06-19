from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./thinkmate_dev.db"
    hf_api_token: str = ""
    hf_model: str = "google/gemma-2-2b-it"
    poe_api_key: str = ""
    poe_model: str = "GPT-4o-Mini"
    poe_base_url: str = "https://api.poe.com/v1"
    admin_password: str = "change-me"
    app_env: str = "development"
    consent_version: str = "v1-2026-06-19"
    seed_demo_students: bool = True
    pilot_access_codes: str = ""
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
