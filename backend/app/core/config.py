
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JobPilot AI"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://jobpilot:jobpilot@localhost:5432/jobpilot"

    secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"
    algorithm: str = "HS256"

    access_token_minutes: int = 20
    refresh_token_days: int = 7

    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False

    resume_storage_dir: str = "private_storage/resumes"
    max_resume_size_bytes: int = 5 * 1024 * 1024

    # Gemini configuration
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str | None = "gemini-3.5-flash-lite"

    telegram_enabled: bool = False
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session_name: str = "jobpilot_telegram"
    telegram_collection_interval_minutes: int = 15
    telegram_channels: str = ""
    auto_match_new_jobs: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
