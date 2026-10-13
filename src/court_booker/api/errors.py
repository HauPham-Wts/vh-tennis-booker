"""Answer engine errors as JSON with a stable code the UI translates."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from court_booker.errors import (
    AppNotReadyError,
    CourtBookerError,
    DeviceError,
    LockHeldError,
    RequestError,
)


class NotFoundError(CourtBookerError):
    """The record asked for does not exist."""


class Problem(BaseModel):
    """An error: ``error`` is a stable code, ``detail`` the English message for the log."""

    error: str
    detail: str


_STATUSES: tuple[tuple[type[CourtBookerError], int, str], ...] = (
    (NotFoundError, 404, "not_found"),
    (LockHeldError, 409, "lock_held"),
    (RequestError, 400, "bad_request"),
    (DeviceError, 503, "device"),
    (AppNotReadyError, 503, "app_not_ready"),
)
"""First match wins: HTTP status and code per error class."""


def problem_for(error: CourtBookerError) -> tuple[int, Problem]:
    """Return the HTTP status and body for ``error``."""
    for kind, status, code in _STATUSES:
        if isinstance(error, kind):
            return status, Problem(error=code, detail=str(error))
    return 500, Problem(error="engine", detail=str(error))


def add_error_handlers(app: FastAPI) -> None:
    """Turn every :class:`CourtBookerError` a route raises into a :class:`Problem`."""

    @app.exception_handler(CourtBookerError)
    async def engine_error(request: Request, error: CourtBookerError) -> JSONResponse:
        status, body = problem_for(error)
        return JSONResponse(status_code=status, content=body.model_dump())
