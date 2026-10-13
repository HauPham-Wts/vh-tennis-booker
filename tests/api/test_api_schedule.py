"""Tests for the schedule routes, with Task Scheduler replaced."""

from datetime import datetime

import pytest

from court_booker import schedule
from court_booker.api import schedule as schedule_routes
from court_booker.config import Config, save_config
from court_booker.errors import ScheduleError


class Evening(datetime):
    """``now`` is the evening of 2026-10-13, after today's start."""

    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 13, 18, 0)


@pytest.fixture
def task(monkeypatch, context):
    """A fake Task Scheduler with the task off, and the time set to the evening."""
    state = {"installed": False, "calls": []}

    def install(config_path, wake_at, run=None, python=None, user=None, today=None):
        state["calls"].append(("install", config_path, wake_at))
        state["installed"] = True

    def remove(run=None):
        state["calls"].append(("remove",))
        state["installed"] = False

    monkeypatch.setattr(schedule, "installed", lambda run=None: state["installed"])
    monkeypatch.setattr(schedule, "install", install)
    monkeypatch.setattr(schedule, "remove", remove)
    monkeypatch.setattr(schedule_routes, "datetime", Evening)
    save_config(Config(wake_at="05:50", start_at="06:00"), context.config_path)
    return state


def test_the_schedule_shows_the_next_booking(client, task):
    assert client.get("/api/schedule").json() == {
        "enabled": False,
        "wake_at": "05:50",
        "start_at": "06:00",
        "next_start": "2026-10-14T06:00",
        "next_play_date": "2026-10-16",
        "dry_run_passed": False,
    }


def test_the_schedule_knows_a_passed_dry_run(client, context, task, record_run):
    record_run(context.data.database, trigger="dry_run", status="ok")
    task["installed"] = True

    state = client.get("/api/schedule").json()

    assert (state["enabled"], state["dry_run_passed"]) == (True, True)


def test_task_scheduler_errors_are_answered(client, monkeypatch, task):
    def broken(run=None):
        raise ScheduleError("schtasks could not run")

    monkeypatch.setattr(schedule, "installed", broken)

    response = client.get("/api/schedule")

    assert response.status_code == 503
    assert response.json()["error"] == "schedule"
