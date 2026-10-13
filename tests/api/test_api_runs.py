"""Tests for starting a dry run, with the process launch replaced."""

import json
import subprocess
import sys
from datetime import datetime

import pytest

from court_booker import processes
from court_booker.api import runs
from court_booker.lock import Holder


class At(datetime):
    moment = datetime(2026, 10, 13, 14, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.moment


class FakeProcess:
    pid = 4321


@pytest.fixture
def launched(monkeypatch):
    """Record dry run launches instead of starting processes; the time is 14:00."""
    calls = []
    monkeypatch.setattr(runs, "launch", lambda path: calls.append(path) or FakeProcess())
    monkeypatch.setattr(runs, "datetime", At)
    return calls


def test_a_dry_run_starts_in_its_own_process(client, context, launched):
    response = client.post("/api/runs/dry-run")

    assert response.status_code == 202
    assert response.json() == {"pid": 4321, "started_at": "2026-10-13T14:00:00"}
    assert launched == [context.config_path.resolve()]


def test_no_dry_run_while_a_run_holds_the_lock(client, context, launched):
    context.data.ensure()
    pid, started = processes.current()
    holder = Holder(pid, started, "scheduled", "2026-10-13T13:59:00")
    context.data.lock.write_text(json.dumps(vars(holder)), encoding="utf-8")

    response = client.post("/api/runs/dry-run")

    assert response.status_code == 409
    assert "scheduled run" in response.json()["detail"]
    assert launched == []


def test_no_dry_run_around_the_scheduled_run(client, launched, monkeypatch):
    monkeypatch.setattr(At, "moment", datetime(2026, 10, 14, 5, 50))

    response = client.post("/api/runs/dry-run")

    assert response.status_code == 400
    assert launched == []


def test_launch_starts_the_dry_run_command(monkeypatch, tmp_path):
    started = []

    def popen(argv, **options):
        started.append((argv, options))
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", popen)

    runs.launch(tmp_path / "config.toml")

    ((argv, options),) = started
    assert argv == [
        sys.executable,
        "-m",
        "court_booker",
        "--dry-run",
        "--config",
        str(tmp_path / "config.toml"),
    ]
    assert options["cwd"] == tmp_path
    assert options["stdout"] is subprocess.DEVNULL
