"""Tests for the device setup routes, with the setup functions replaced."""

import json
from datetime import datetime

import pytest

from court_booker import device_setup, history_read, processes
from court_booker.device_setup import Check, Status
from court_booker.lock import Holder

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


class At(datetime):
    """``now`` is 14:00, outside the scheduled run's window."""

    moment = datetime(2026, 10, 13, 14, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.moment


@pytest.fixture
def fixes(monkeypatch):
    """Replace auto setup: it fixes the wake timers and records how it was called."""
    calls = []

    def auto_setup(config, config_path, tools, *, restart_mumu=False, run=None):
        calls.append(restart_mumu)
        return [Check("wake_timers", Status.FIXED, "Wake timers enabled")]

    monkeypatch.setattr(device_setup, "find_tools", lambda config: "tools")
    monkeypatch.setattr(device_setup, "auto_setup", auto_setup)
    monkeypatch.setattr(device_setup, "datetime", At)
    return calls


def setup_steps(context):
    connection = history_read.open_read_only(context.data.database)
    steps = history_read.list_events(connection, category="setup")
    connection.close()
    return [step["kind"] for step in reversed(steps)]


def test_auto_setup_fixes_and_records_each_item(client, context, fixes):
    response = client.post("/api/setup/auto", json={"restart_mumu": True})

    assert response.status_code == 200
    assert response.json() == [
        {"item": "wake_timers", "status": "fixed", "detail": "Wake timers enabled"}
    ]
    assert fixes == [True]
    assert setup_steps(context) == ["setup_started", "setup_item", "setup_finished"]
    assert not context.data.lock.exists()


def test_auto_setup_waits_for_a_run(client, context, fixes):
    context.data.ensure()
    pid, started = processes.current()
    holder = Holder(pid, started, "dry_run", "2026-10-13T13:59:00")
    context.data.lock.write_text(json.dumps(vars(holder)), encoding="utf-8")

    response = client.post("/api/setup/auto", json={})

    assert response.status_code == 409
    assert response.json()["error"] == "lock_held"
    assert fixes == []


def test_no_auto_setup_around_the_scheduled_run(client, fixes, monkeypatch):
    monkeypatch.setattr(At, "moment", datetime(2026, 10, 14, 5, 55))

    response = client.post("/api/setup/auto", json={})

    assert response.status_code == 400
    assert response.json()["detail"].startswith("No auto setup from 05:45 to 06:05")
    assert fixes == []
