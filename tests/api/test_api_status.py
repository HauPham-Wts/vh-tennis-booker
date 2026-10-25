"""Tests for the Overview status."""

import json
from datetime import datetime

import pytest

from court_booker import __version__, processes, schedule
from court_booker.api import schedule as schedule_routes
from court_booker.api import status
from court_booker.api.activity import record
from court_booker.config import Config, save_config
from court_booker.events import EventKind
from court_booker.lock import Holder


class Process:
    pid = 4321

    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


def hold_lock(context, trigger="scheduled"):
    context.data.ensure()
    pid, started = processes.current()
    holder = Holder(pid, started, trigger, "2026-10-14T05:50:01")
    context.data.lock.write_text(json.dumps(vars(holder)), encoding="utf-8")
    return pid


def test_nothing_runs(context):
    assert status.running(context) is None
    assert status.running(context, Process(code=0)) is None


def test_the_lock_holder_runs(context):
    pid = hold_lock(context)

    assert status.running(context, Process()).model_dump() == {
        "trigger": "scheduled",
        "pid": pid,
        "since": "2026-10-14T05:50:01",
        "runs": [],
    }


def test_a_starting_dry_run_runs(context):
    assert status.running(context, Process()).model_dump() == {
        "trigger": "dry_run",
        "pid": 4321,
        "since": None,
        "runs": [],
    }


def run(run_id, started_at, device):
    return {"id": run_id, "started_at": f"2026-10-14T{started_at}", "device": device}


def test_the_holder_runs_with_the_runs_of_its_instances():
    recent = [  # newest first, as the History lists them
        run(9, "05:50:03.400", 2),
        run(8, "05:50:03.300", 1),
        run(7, "05:50:01.200", 0),
        run(6, "05:50:00.900", 1),  # an instance's run of the run before
    ]

    assert status.runs_of("2026-10-14T05:50:01", recent, own=0) == [7, 8, 9]


def test_a_run_of_one_instance_runs_alone():
    recent = [run(7, "05:50:01.200", None), run(6, "05:49:00.000", None)]  # before 0.13.0

    assert status.runs_of("2026-10-14T05:50:01", recent, own=0) == [7]


def test_the_holder_has_no_run_until_its_own_starts():
    recent = [run(6, "05:40:00.000", 0)]  # the last run, from before the lock was taken

    assert status.runs_of("2026-10-14T05:50:01", recent, own=0) == []


@pytest.fixture
def evening(monkeypatch, context):
    """Task Scheduler says the task is on; the time is the evening of 2026-10-13."""
    monkeypatch.setattr(schedule, "installed", lambda run=None: True)
    monkeypatch.setattr(schedule_routes, "datetime", Evening)
    save_config(Config(wake_at="05:50", start_at="06:00"), context.config_path)


class Evening(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 13, 18, 0)


def test_status_on_a_new_install(client, evening):
    body = client.get("/api/status").json()

    assert body["version"] == __version__
    assert body["running"] is None
    assert body["last_run"] is None
    assert body["setup"] is None
    assert body["schedule"]["next_start"] == "2026-10-14T06:00"


def test_status_shows_the_last_run_and_setup(client, context, evening, record_run):
    record_run(context.data.database, slots=[("18:00 - 19:00", True)])
    record(context, EventKind.SETUP_FINISHED, left=["app_installed"], error=None)

    body = client.get("/api/status").json()

    assert (body["last_run"]["status"], body["last_run"]["booked"]) == ("ok", 1)
    assert body["setup"]["left"] == ["app_installed"]


def test_status_shows_the_run_going_on(client, context, evening):
    pid = hold_lock(context, trigger="dry_run")

    assert client.get("/api/status").json()["running"]["pid"] == pid
