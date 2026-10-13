"""Tests for reading the history back."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from court_booker import history, history_read
from court_booker.events import EventKind, Reporter


class Clock:
    """Moves one second per reading."""

    def __init__(self):
        self.now = datetime(2026, 10, 13, 5, 50)

    def __call__(self):
        self.now += timedelta(seconds=1)
        return self.now


def record_run(path, trigger="scheduled", date="2026-10-15", slots=(), status="ok", clock=None):
    """Write one run through the history sink, as a real run does; return its id."""
    connection = history.connect(path)
    store = history.History(connection)
    report = Reporter(store, clock=clock or Clock())
    report(EventKind.RUN_STARTED, trigger=trigger, dry_run=trigger == "dry_run", version="0.5.0")
    if date:
        report(EventKind.BOOKING_STARTED, date=date, court="S6 - Sân tennis", slots=[])
    for slot, ok in slots:
        report(EventKind.SLOT_STARTED, slot=slot, round=1, rounds=len(slots))
        if ok:
            report(EventKind.SLOT_BOOKED, slot=slot, seconds=7.8, commands=51, dry_run=False)
        else:
            report(
                EventKind.SLOT_FAILED, slot=slot, reason="fully booked", seconds=2.1, commands=12
            )
    report(EventKind.RUN_FINISHED, status=status, booked=0, total=0, error=None)
    store.close()
    return store.run_id


@pytest.fixture
def path(tmp_path):
    return tmp_path / "booker.db"


@pytest.fixture
def read(path):
    connections = []

    def open_it():
        connection = history_read.open_read_only(path)
        connections.append(connection)
        return connection

    yield open_it
    for connection in connections:
        connection.close()


def test_a_missing_database_reads_as_empty(tmp_path):
    connection = history_read.open_read_only(tmp_path / "data" / "booker.db")

    assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    connection.close()


def test_the_app_cannot_write(tmp_path):
    path = tmp_path / "booker.db"
    history.connect(path).close()
    connection = history_read.open_read_only(path)

    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        connection.execute("DELETE FROM runs")
    connection.close()


def test_runs_come_newest_first_with_their_slot_counts(path, read):
    first = record_run(
        path, slots=[("18:00 - 19:00", True), ("19:00 - 20:00", False)], status="partial"
    )
    second = record_run(path, trigger="dry_run", slots=[("10:00 - 11:00", True)])

    runs = history_read.list_runs(read())

    assert [run["id"] for run in runs] == [second, first]
    assert runs[0]["dry_run"] is True
    assert (runs[1]["booked"], runs[1]["total"], runs[1]["status"]) == (1, 2, "partial")
    assert runs[1]["court"] == "S6 - Sân tennis"


def test_runs_filter_by_play_month_and_trigger(path, read):
    october = record_run(path, date="2026-10-31")
    record_run(path, date="2026-11-01")
    record_run(path, trigger="dry_run", date="2026-10-15")

    assert [
        r["id"] for r in history_read.list_runs(read(), month="2026-10", trigger="scheduled")
    ] == [october]


def test_runs_page_back_from_a_run(path, read):
    ids = [record_run(path) for _ in range(5)]

    page = history_read.list_runs(read(), before=ids[3], limit=2)

    assert [run["id"] for run in page] == [ids[2], ids[1]]


def test_one_run_comes_with_slots_steps_and_log_lines(path, read):
    run_id = record_run(path, slots=[("18:00 - 19:00", True), ("19:00 - 20:00", False)])

    run = history_read.get_run(read(), run_id)

    assert [(slot["slot"], slot["ok"], slot["reason"]) for slot in run["slots"]] == [
        ("18:00 - 19:00", True, None),
        ("19:00 - 20:00", False, "fully booked"),
    ]
    assert [step["kind"] for step in run["steps"]][:2] == ["run_started", "booking_started"]
    assert run["steps"][1]["data"]["court"] == "S6 - Sân tennis"
    assert run["log_lines"] == []  # the sink alone logs nothing


def test_an_unknown_run_is_none(path, read):
    assert history_read.get_run(read(), 42) is None


def test_activity_comes_newest_first_and_filters_by_category(path, read):
    record_run(path, slots=[("18:00 - 19:00", False)])

    steps = history_read.list_events(read())
    errors = history_read.list_events(read(), category="error")

    assert steps[0]["kind"] == "run_finished"
    assert steps[-1]["kind"] == "run_started"
    assert [step["kind"] for step in errors] == ["slot_failed"]
    assert errors[0]["data"]["reason"] == "fully booked"


def test_activity_pages_back(path, read):
    record_run(path)
    newest = history_read.list_events(read(), limit=1)

    older = history_read.list_events(read(), before=newest[0]["id"], limit=1)

    assert older[0]["id"] == newest[0]["id"] - 1
