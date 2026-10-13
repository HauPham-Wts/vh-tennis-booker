"""Tests for the schedule routes, with Task Scheduler replaced."""

from datetime import datetime

import pytest

from court_booker import history_read, schedule
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


def schedule_steps(context):
    connection = history_read.open_read_only(context.data.database)
    steps = history_read.list_events(connection, category="schedule")
    connection.close()
    return [(step["kind"], step["data"]) for step in reversed(steps)]


def test_the_schedule_needs_a_passed_dry_run(client, context, task):
    response = client.put("/api/schedule", json={"enabled": True})

    assert response.status_code == 409
    assert response.json()["error"] == "dry_run_required"
    assert task["calls"] == []


def test_switching_on_installs_the_task_and_records_it(client, context, task, record_run):
    record_run(context.data.database, trigger="dry_run", status="ok")

    response = client.put("/api/schedule", json={"enabled": True})

    assert response.json()["enabled"] is True
    assert task["calls"] == [("install", context.config_path.resolve(), "05:50")]
    assert schedule_steps(context) == [
        ("schedule_enabled", {"wake_at": "05:50", "start_at": "06:00"})
    ]


def test_switching_off_removes_the_task(client, context, task):
    task["installed"] = True

    response = client.put("/api/schedule", json={"enabled": False})

    assert response.json()["enabled"] is False
    assert task["calls"] == [("remove",)]
    assert schedule_steps(context) == [("schedule_disabled", {})]


def test_switching_off_an_off_schedule_does_nothing(client, context, task):
    client.put("/api/schedule", json={"enabled": False})

    assert task["calls"] == []
    assert schedule_steps(context) == []


def test_a_wake_time_after_the_start_is_refused(client, context, task, record_run):
    record_run(context.data.database, trigger="dry_run", status="ok")
    # Only a hand edit can do this: saving from the app checks the times.
    context.config_path.write_text('wake_at = "06:30"\nstart_at = "06:00"\n', encoding="utf-8")

    response = client.put("/api/schedule", json={"enabled": True})

    assert response.status_code == 400
    assert task["calls"] == []
