from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./thinkmate_dev.db"
    hf_api_token: str = ""
    hf_model: str = "google/gemma-2-2b-it"
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
