# omagent/core/config.py
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Centralized configuration for omagent."""

    # LLM
    model: str = "anthropic/claude-sonnet-4-6"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: str | None = None  # Bearer token; if None, auth disabled (dev mode)

    # Domain pack
    default_pack: str = "default"

    # Storage
    db_path: Path = Path.home() / ".omagent" / "sessions.db"

    # Agent loop
    max_iterations: int = 20
    default_permission: str = "prompt"

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"  # "text" or "json"

    model_config = {
        "env_prefix": "OMAGENT_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_config() -> Config:
    return Config()
