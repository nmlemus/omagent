# omagent/server/app.py
import logging
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omagent.core.config import get_config
from omagent.server.routes import create_router

logger = logging.getLogger(__name__)


def create_app(
    default_pack: str = "default",
    loop_factory: Callable | None = None,
) -> FastAPI:
    """Create the FastAPI application."""
    config = get_config()

    if config.api_key is None:
        logger.warning(
            "No OMAGENT_API_KEY set — server running without authentication. "
            "Set OMAGENT_API_KEY env var for production use."
        )

    app = FastAPI(
        title="omagent",
        description="Oh My Agent — Generic domain-configurable agentic engine",
        version="0.1.0",
    )

    origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store config in app state
    app.state.default_pack = default_pack
    app.state.loop_factory = loop_factory

    router = create_router()
    app.include_router(router)

    return app
