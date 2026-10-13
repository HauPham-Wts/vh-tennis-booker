"""Build the FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from court_booker import __version__


class Health(BaseModel):
    """The backend answers and runs this version."""

    status: str
    version: str


def create_app() -> FastAPI:
    """Return the backend; its OpenAPI schema is served at ``/api/openapi.json``."""
    app = FastAPI(
        title="Court Booker",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )

    @app.get("/api/health", response_model=Health, tags=["app"])
    def health() -> Health:
        """Tell the UI the backend is up, and its version."""
        return Health(status="ok", version=__version__)

    return app
