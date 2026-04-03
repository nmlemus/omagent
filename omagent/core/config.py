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


def setup_logging(config: Config | None = None) -> None:
    """Configure the root logger based on Config settings."""
    import logging
    import sys

    cfg = config or get_config()
    level = getattr(logging, cfg.log_level.upper(), logging.INFO)

    if cfg.log_format == "json":
        import json as _json
        from datetime import datetime, timezone

        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                return _json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "line": record.lineno,
                }, default=str)

        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JSONFormatter())
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
