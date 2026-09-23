from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "STT Platform"
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 720

    database_url: str = "postgresql+psycopg://stt:stt@localhost:5432/stt"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:9001"

    storage_path: str = "./data/storage"
    temp_path: str = "./data/temp"
    whisper_model_dir: str = "./data/models"

    device: str = "auto"
    compute_type: str = "float16"
    gpu_index: int = 0

    admin_email: str = ""
    admin_password: str = ""
    admin_name: str = "مدیر سیستم"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
