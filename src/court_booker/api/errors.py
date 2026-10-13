"""Answer errors as JSON with a stable code the UI translates."""

# No `from __future__ import annotations`: Pydantic reads the annotations at run time.
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from court_booker.errors import (
    AppNotReadyError,
    CourtBookerError,
    DeviceError,
    LockHeldError,
    RequestError,
    ScheduleError,
)


class NotFoundError(CourtBookerError):
    """The record asked for does not exist."""


class InvalidSettingsError(CourtBookerError):
    """Settings a run could not use; ``problems`` names each invalid value."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class Problem(BaseModel):
    """An error: ``error`` is a stable code, ``detail`` the English message for the log.

    ``problems`` lists each invalid value when there are several, one line per value.
    """

    error: str
    detail: str
    problems: Optional[list[str]] = None


_STATUSES: tuple[tuple[type[CourtBookerError], int, str], ...] = (
    (NotFoundError, 404, "not_found"),
    (LockHeldError, 409, "lock_held"),
    (RequestError, 400, "bad_request"),
    (DeviceError, 503, "device"),
    (AppNotReadyError, 503, "app_not_ready"),
    (ScheduleError, 503, "schedule"),
)
"""First match wins: HTTP status and code per error class."""


def problem_for(error: CourtBookerError) -> tuple[int, Problem]:
    """Return the HTTP status and body for ``error``."""
    if isinstance(error, InvalidSettingsError):
        return 422, Problem(error="invalid_settings", detail=str(error), problems=error.problems)
    for kind, status, code in _STATUSES:
        if isinstance(error, kind):
            return status, Problem(error=code, detail=str(error))
    return 500, Problem(error="engine", detail=str(error))


def answer(status: int, problem: Problem) -> JSONResponse:
    """Return ``problem`` as the response body."""
    return JSONResponse(status_code=status, content=problem.model_dump(exclude_none=True))


def add_error_handlers(app: FastAPI) -> None:
    """Answer engine errors and invalid requests with a :class:`Problem`."""

    @app.exception_handler(CourtBookerError)
    async def engine_error(request: Request, error: CourtBookerError) -> JSONResponse:
        return answer(*problem_for(error))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        problems = [
            f"{'.'.join(str(part) for part in item['loc'][1:])}: {item['msg']}"
            for item in error.errors()
        ]
        return answer(
            422, Problem(error="invalid_request", detail="; ".join(problems), problems=problems)
        )
