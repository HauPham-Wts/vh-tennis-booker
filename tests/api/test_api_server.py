"""Tests for ``court-booker serve`` with uvicorn replaced."""

import pytest
import uvicorn

from court_booker.api import server
from court_booker.config import load_config


@pytest.fixture
def served(monkeypatch):
    """Record what uvicorn would serve instead of serving it."""
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: calls.append((app, options)))
    return calls


def test_serves_on_this_pc_only(served, tmp_path):
    config_path = tmp_path / "config.toml"

    assert server.main(["--config", str(config_path), "--port", "9000"]) == 0

    ((app, options),) = served
    assert options["host"] == "127.0.0.1"
    assert options["port"] == 9000
    assert app.state.context.config_path == config_path.resolve()


def test_the_data_folder_config_is_created_when_none_is_given(served, data_home):
    server.main([])

    ((app, _),) = served
    assert app.state.context.config_path == data_home / "config.toml"
    assert load_config(data_home / "config.toml").days_ahead == 2
    assert app.state.context.data.root == data_home
