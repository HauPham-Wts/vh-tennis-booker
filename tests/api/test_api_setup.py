"""Tests for the device setup routes, with the setup functions replaced."""

import pytest

from court_booker import device_setup
from court_booker.device_setup import Check, Status

CHECKS = [
    Check("mumu_installed", Status.OK, "MuMu at C:/MuMu/MuMuManager.exe"),
    Check("wake_timers", Status.FIXABLE, "Wake timers disabled on battery"),
    Check("app_installed", Status.UNKNOWN, "Start MuMu to check the app"),
]


@pytest.fixture
def checks(monkeypatch):
    monkeypatch.setattr(device_setup, "find_tools", lambda config: "tools")
    monkeypatch.setattr(device_setup, "run_checks", lambda config, tools, run=None: CHECKS)


def test_setup_lists_each_item(client, checks):
    response = client.get("/api/setup")

    assert response.status_code == 200
    assert response.json() == [
        {"item": "mumu_installed", "status": "ok", "detail": "MuMu at C:/MuMu/MuMuManager.exe"},
        {"item": "wake_timers", "status": "fixable", "detail": "Wake timers disabled on battery"},
        {"item": "app_installed", "status": "unknown", "detail": "Start MuMu to check the app"},
    ]
