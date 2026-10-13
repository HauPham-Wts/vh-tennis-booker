"""Tests for the history database."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta

import pytest

from court_booker import history
from court_booker.events import EventKind, Reporter

START = datetime(2026, 10, 13, 5, 50, 3, 257000)


@pytest.fixture
def connection(tmp_path):
    connection = history.connect(tmp_path / "booker.db")
    yield connection
    connection.close()


def ticking_clock():
    """Return a clock that moves one second per call."""
    moments = (START + timedelta(seconds=step) for step in range(1000))
    return lambda: next(moments)


def play_run(report):
    """Report a two-slot scheduled run where the second slot is fully booked."""
    report(
        EventKind.RUN_STARTED,
        trigger="scheduled",
        dry_run=False,
        slots=["18:00 - 19:00", "19:00 - 20:00"],
        start="2026-10-13T06:00:00",
        version="0.5.0",
    )
    report(EventKind.DEVICE_READY)
    report(EventKind.APP_READY)
    report(
        EventKind.BOOKING_STARTED,
        date="2026-10-15",
        court="S6 - Sân tennis",
        slots=["18:00 - 19:00", "19:00 - 20:00"],
        dry_run=False,
    )
    report(EventKind.SLOT_STARTED, slot="18:00 - 19:00", round=1, rounds=2)
    report(EventKind.SLOT_BOOKED, slot="18:00 - 19:00", seconds=7.8, commands=51, dry_run=False)
    report(EventKind.SLOT_STARTED, slot="19:00 - 20:00", round=2, rounds=2)
    report(
        EventKind.SLOT_FAILED,
        slot="19:00 - 20:00",
        reason="Slot 19:00 - 20:00 is fully booked",
        seconds=2.1,
        commands=12,
    )
    report(EventKind.RUN_FINISHED, status="partial", booked=1, total=2, error=None)


def rows(connection, sql):
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(sql)]


def tables(connection):
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {name for (name,) in rows}


def test_connect_creates_the_tables(tmp_path):
    connection = history.connect(tmp_path / "data" / "booker.db")

    assert tables(connection) == {"runs", "run_slots", "events", "log_lines"}
    assert connection.execute("PRAGMA user_version").fetchone()[0] == history.SCHEMA_VERSION
    assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    connection.close()


def test_migrate_twice_changes_nothing(connection):
    assert history.migrate(connection) == history.SCHEMA_VERSION
    assert history.migrate(connection) == history.SCHEMA_VERSION


def test_newer_database_is_left_as_it_is(connection):
    connection.execute(f"PRAGMA user_version = {history.SCHEMA_VERSION + 1}")

    assert history.migrate(connection) == history.SCHEMA_VERSION + 1
    assert tables(connection) == {"runs", "run_slots", "events", "log_lines"}


def test_slots_need_an_existing_run(connection):
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO run_slots (run_id, slot, ok, finished_at, seconds, commands)"
            " VALUES (99, '18:00 - 19:00', 1, '2026-10-13T06:00:07', 7.0, 16)"
        )


def test_a_run_and_its_slots_are_recorded(connection):
    store = history.History(connection)

    play_run(Reporter(store, clock=ticking_clock()))

    assert rows(connection, "SELECT * FROM runs") == [
        {
            "id": store.run_id,
            "trigger": "scheduled",
            "dry_run": 0,
            "version": "0.5.0",
            "started_at": "2026-10-13T05:50:03.257",
            "finished_at": "2026-10-13T05:50:11.257",
            "play_date": "2026-10-15",
            "court": "S6 - Sân tennis",
            "status": "partial",
            "error": None,
        }
    ]
    assert rows(connection, "SELECT * FROM run_slots") == [
        {
            "id": 1,
            "run_id": store.run_id,
            "slot": "18:00 - 19:00",
            "ok": 1,
            "reason": None,
            "finished_at": "2026-10-13T05:50:08.257",
            "seconds": 7.8,
            "commands": 51,
        },
        {
            "id": 2,
            "run_id": store.run_id,
            "slot": "19:00 - 20:00",
            "ok": 0,
            "reason": "Slot 19:00 - 20:00 is fully booked",
            "finished_at": "2026-10-13T05:50:10.257",
            "seconds": 2.1,
            "commands": 12,
        },
    ]


def test_a_run_stays_running_until_it_finishes(connection):
    report = Reporter(history.History(connection), clock=ticking_clock())

    report(EventKind.RUN_STARTED, trigger="dry_run", dry_run=True, version="0.5.0")

    assert rows(connection, "SELECT status, finished_at FROM runs") == [
        {"status": "running", "finished_at": None}
    ]


def test_every_event_becomes_an_activity_step(connection):
    store = history.History(connection)

    play_run(Reporter(store, clock=ticking_clock()))

    steps = rows(connection, "SELECT run_id, category, kind FROM events ORDER BY id")
    assert {step["run_id"] for step in steps} == {store.run_id}
    assert [(step["category"], step["kind"]) for step in steps] == [
        ("step", "run_started"),
        ("step", "device_ready"),
        ("step", "app_ready"),
        ("step", "booking_started"),
        ("slot", "slot_started"),
        ("slot", "slot_booked"),
        ("slot", "slot_started"),
        ("error", "slot_failed"),
        ("step", "run_finished"),
    ]


def test_step_data_is_kept_as_json(connection):
    play_run(Reporter(history.History(connection), clock=ticking_clock()))

    query = "SELECT data FROM events WHERE kind = 'booking_started'"
    (data,) = connection.execute(query).fetchone()
    assert '"court": "S6 - Sân tennis"' in data
    assert json.loads(data)["slots"] == ["18:00 - 19:00", "19:00 - 20:00"]


def test_a_run_that_ends_with_an_error_is_an_error_step(connection):
    report = Reporter(history.History(connection), clock=ticking_clock())

    report(EventKind.RUN_STARTED, trigger="scheduled", dry_run=False, version="0.5.0")
    report(EventKind.RUN_FINISHED, status="failed", booked=0, total=0, error="adb lost")

    assert rows(connection, "SELECT category FROM events WHERE kind = 'run_finished'") == [
        {"category": "error"}
    ]


def test_a_database_error_turns_history_off_once(connection, caplog):
    caplog.set_level(logging.WARNING, logger="court_booker")
    store = history.History(connection)
    report = Reporter(store, clock=ticking_clock())
    connection.close()

    play_run(report)

    assert store.failed
    assert caplog.text.count("History database failed") == 1
    assert "Event sink failed" not in caplog.text
