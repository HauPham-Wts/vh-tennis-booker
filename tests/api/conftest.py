"""Backend tests: skipped without the ``app`` extra (FastAPI)."""

import importlib.util

import pytest

collect_ignore_glob = [] if importlib.util.find_spec("fastapi") else ["test_*.py"]


@pytest.fixture
def context(tmp_path, data_home):
    """A backend context with its config file in ``tmp_path`` and the test data folder."""
    from court_booker.api.context import AppContext
    from court_booker.paths import DataFolder

    return AppContext(tmp_path / "config.toml", DataFolder(data_home))


@pytest.fixture
def app(context):
    from court_booker.api.app import create_app

    return create_app(context)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def wake_timers(monkeypatch):
    """Keep ``powercfg`` out of the tests: wake timers are allowed; set ``status`` to change.

    ``calls`` counts the times the schedule allowed them.
    """
    from court_booker import device_setup
    from court_booker.device_setup import Check, Status

    state = {"status": Status.OK, "calls": 0}

    def check(run=None):
        return Check(device_setup.WAKE_TIMERS, state["status"], "Wake timers")

    def ensure(run=None):
        state["calls"] += 1
        return check()

    monkeypatch.setattr(device_setup, "check_wake_timers", check)
    monkeypatch.setattr(device_setup, "ensure_wake_timers", ensure)
    return state
