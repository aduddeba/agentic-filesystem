"""Application settings, sourced from environment variables / `.env`."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_STORAGE_ROOT = str(Path(__file__).resolve().parent.parent / "storage")


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_filesystem"
    storage_root: str = DEFAULT_STORAGE_ROOT
    cors_origins: str = "http://localhost:3000"

    ollama_host: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:1b"
    ollama_embed_model: str = "all-minilm"
    planner_max_steps: int = 8
    planner_max_replans: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
Path(settings.storage_root).mkdir(parents=True, exist_ok=True)

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def set_storage_root(path: str) -> None:
    """Point `settings.storage_root` at `path` and persist the change to `.env`.

    Updates the in-memory setting immediately (everything that reads
    `settings.storage_root` does so live, not at import time) and rewrites the
    `STORAGE_ROOT=` line in `.env` so the choice survives a restart too.
    """
    settings.storage_root = path

    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines() if _ENV_PATH.exists() else []
    new_line = f"STORAGE_ROOT={path}"
    for i, line in enumerate(lines):
        if line.startswith("STORAGE_ROOT="):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)

    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
