"""Application settings, sourced from environment variables / `.env`."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_STORAGE_ROOT = str(Path(__file__).resolve().parent.parent / "storage")


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_filesystem"
    storage_root: str = DEFAULT_STORAGE_ROOT
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
Path(settings.storage_root).mkdir(parents=True, exist_ok=True)
