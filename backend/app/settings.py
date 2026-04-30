from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_DB_DIR = BACKEND_ROOT / "db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"
    environment: str = "production"

    # Storage
    db_dir: Path = DEFAULT_DB_DIR
    history_db_path: Path | None = None

    # Upload limits
    max_upload_bytes: int = 20 * 1024 * 1024
    max_upload_rows: int = 1_000_000
    max_request_bytes: int = 1 * 1024 * 1024  # non-upload requests

    # SQL execution limits
    sql_query_timeout_seconds: float = 10.0
    sql_progress_handler_n: int = 1000
    sql_max_row_limit: int = 1000

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str | None = None
    ollama_attempt_timeouts: str = "45.0,180.0"
    ollama_model_cache_ttl_seconds: int = 300

    # Gemini
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 60.0

    # Agentic tool-calling — when enabled and Gemini is configured, the LLM probes
    # the database via tools instead of getting a static schema dump.
    llm_use_tools: bool = True
    llm_max_tool_iterations: int = 8

    # Rate limits (requests per window). Format: "<count>/<unit>"
    rate_limit_enabled: bool = True
    rate_limit_default: str = "120/minute"
    rate_limit_ask: str = "10/minute"
    rate_limit_execute: str = "30/minute"
    rate_limit_upload: str = "20/hour"

    @field_validator("db_dir", mode="before")
    @classmethod
    def _coerce_db_dir(cls, value: object) -> Path:
        if value is None or value == "":
            return DEFAULT_DB_DIR
        return Path(value).expanduser().resolve()

    @field_validator("history_db_path", mode="before")
    @classmethod
    def _coerce_history_db_path(cls, value: object) -> Path | None:
        if value is None or value == "":
            return None
        return Path(value).expanduser().resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ollama_chat_url(self) -> str:
        return self.ollama_url.rstrip("/") + "/api/chat"

    @property
    def ollama_tags_url(self) -> str:
        return self.ollama_url.rstrip("/") + "/api/tags"

    @property
    def attempt_timeouts(self) -> tuple[float, ...]:
        parts = [p.strip() for p in self.ollama_attempt_timeouts.split(",") if p.strip()]
        return tuple(float(p) for p in parts) or (45.0, 180.0)

    @property
    def effective_history_db_path(self) -> Path:
        return self.history_db_path or (self.db_dir / "query_history.sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Test helper — clears the cache and re-reads env."""
    get_settings.cache_clear()
    return get_settings()


# Convenience for env var lookups that pre-date the settings module.
def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")
