"""Build the FastAPI application."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from court_booker import __version__
from court_booker.api import history, live, runs, schedule, settings, setup, status
from court_booker.api.context import AppContext
from court_booker.api.errors import Problem, add_error_handlers

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": Problem, "description": "Invalid request values, one line per value"},
    "default": {"model": Problem, "description": "An error with a stable code"},
}
"""Every route answers errors as a Problem; this tells the schema (and the UI types) so."""


class Health(BaseModel):
    """The backend answers and runs this version."""

    status: str
    version: str


def create_app(context: AppContext) -> FastAPI:
    """Return the backend for ``context``; its OpenAPI schema is at ``/api/openapi.json``."""
    app = FastAPI(
        title="Court Booker",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.context = context
    add_error_handlers(app)

    @app.get("/api/health", response_model=Health, tags=["app"], responses=ERROR_RESPONSES)
    def health() -> Health:
        """Tell the UI the backend is up, and its version."""
        return Health(status="ok", version=__version__)

    for module in (history, settings, setup, schedule, runs, status):
        app.include_router(module.router, responses=ERROR_RESPONSES)
    app.include_router(live.router)
    return app
