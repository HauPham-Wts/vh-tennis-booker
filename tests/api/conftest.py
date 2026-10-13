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
