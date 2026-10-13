"""Build the FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from court_booker import __version__
from court_booker.api import history
from court_booker.api.context import AppContext
from court_booker.api.errors import add_error_handlers


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

    @app.get("/api/health", response_model=Health, tags=["app"])
    def health() -> Health:
        """Tell the UI the backend is up, and its version."""
        return Health(status="ok", version=__version__)

    app.include_router(history.router)
    return app
