# omagent/server/app.py
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omagent.server.routes import create_router


def create_app(
    default_pack: str = "default",
    loop_factory: Callable | None = None,
) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="omagent",
        description="Oh My Agent — Generic domain-configurable agentic engine",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
