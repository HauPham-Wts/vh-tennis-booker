"""Tests for engine errors answered by the backend."""

import pytest

from court_booker.api.errors import NotFoundError
from court_booker.config import ConfigError
from court_booker.errors import (
    AppNotReadyError,
    CourtBookerError,
    EmulatorError,
    LockHeldError,
    RequestError,
)


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (LockHeldError("Another run is in progress: dry_run run"), 409, "lock_held"),
        (RequestError("No dry run from 05:50 to 06:05"), 400, "bad_request"),
        (ConfigError("Unknown config key: 'x'"), 400, "bad_request"),
        (EmulatorError("MuMu did not start"), 503, "device"),
        (AppNotReadyError("The app did not show 'Tiện ích'"), 503, "app_not_ready"),
        (CourtBookerError("Something else"), 500, "engine"),
    ],
)
def test_engine_errors_become_problems(app, client, error, status, code):
    @app.get("/api/test-error")
    def fail() -> None:
        raise error

    response = client.get("/api/test-error")

    assert response.status_code == status
    assert response.json() == {"error": code, "detail": str(error)}


def test_a_missing_record_is_not_found(app, client):
    @app.get("/api/test-missing")
    def fail() -> None:
        raise NotFoundError("No run 42")

    assert client.get("/api/test-missing").status_code == 404
