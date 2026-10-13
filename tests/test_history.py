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


def test_app_events_have_their_own_categories(connection):
    report = Reporter(history.History(connection), clock=ticking_clock())

    report(EventKind.SETUP_ITEM, item="wake_timers", status="fixed", detail="enabled")
    report(EventKind.SETTINGS_SAVED, changed=["slots"])

    assert rows(connection, "SELECT run_id, category FROM events ORDER BY id") == [
        {"run_id": None, "category": "setup"},
        {"run_id": None, "category": "settings"},
    ]


def test_a_run_that_ends_with_an_error_is_an_error_step(connection):
    report = Reporter(history.History(connection), clock=ticking_clock())

    report(EventKind.RUN_STARTED, trigger="scheduled", dry_run=False, version="0.5.0")
    report(EventKind.RUN_FINISHED, status="failed", booked=0, total=0, error="adb lost")

    assert rows(connection, "SELECT category FROM events WHERE kind = 'run_finished'") == [
        {"category": "error"}
    ]


@pytest.fixture
def capture(connection):
    """Return a history whose handler listens to a test logger, and that logger."""
    store = history.History(connection)
    log = logging.getLogger("court_booker.tests.history")
    log.setLevel(logging.DEBUG)
    log.addHandler(store.handler)
    yield store, log
    log.removeHandler(store.handler)


def log_lines(connection):
    return rows(connection, "SELECT run_id, level, message FROM log_lines ORDER BY id")


def test_lines_before_the_run_are_stored_with_it(connection, capture):
    store, log = capture
    report = Reporter(store, clock=ticking_clock())

    log.info("court-booker 0.5.0")
    assert log_lines(connection) == []
    report(EventKind.RUN_STARTED, trigger="manual", dry_run=False, version="0.5.0")
    log.debug("Connected to 127.0.0.1:16384")

    assert log_lines(connection) == [
        {"run_id": store.run_id, "level": "INFO", "message": "court-booker 0.5.0"},
        {"run_id": store.run_id, "level": "DEBUG", "message": "Connected to 127.0.0.1:16384"},
    ]


def test_lines_without_a_run_are_stored_on_close(connection, capture):
    store, log = capture

    log.error("Unknown config key: 'unknown'")
    log.removeHandler(store.handler)
    store.handler.close()

    assert log_lines(connection) == [
        {"run_id": None, "level": "ERROR", "message": "Unknown config key: 'unknown'"}
    ]


def test_a_line_keeps_its_traceback_and_time(connection, capture):
    store, log = capture
    Reporter(store, clock=ticking_clock())(
        EventKind.RUN_STARTED, trigger="manual", dry_run=False, version="0.5.0"
    )

    try:
        raise OSError("adb lost")
    except OSError:
        log.exception("Unexpected error")

    ((time, message),) = connection.execute("SELECT time, message FROM log_lines").fetchall()
    assert message.startswith("Unexpected error\nTraceback")
    assert message.endswith("OSError: adb lost")
    assert datetime.fromisoformat(time) <= datetime.now()


def test_logging_goes_on_when_the_database_fails(connection, capture):
    store, log = capture
    Reporter(store, clock=ticking_clock())(
        EventKind.RUN_STARTED, trigger="manual", dry_run=False, version="0.5.0"
    )
    connection.close()

    log.info("Tapped 'Sân Tennis'")
    log.info("Selected date 2026-10-15")

    assert store.failed


def test_runs_left_running_are_marked_interrupted(connection, caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    started = {"trigger": "dry_run", "dry_run": True, "version": "0.5.0"}
    Reporter(history.History(connection), clock=ticking_clock())(EventKind.RUN_STARTED, **started)
    store = history.History(connection)
    Reporter(store, clock=ticking_clock())(EventKind.RUN_STARTED, **started)

    store.interrupt_stale_runs()

    assert rows(connection, "SELECT id, status FROM runs ORDER BY id") == [
        {"id": 1, "status": "interrupted"},
        {"id": 2, "status": "running"},
    ]
    assert "Marked 1 run(s) left running as interrupted" in caplog.text


def test_a_database_error_turns_history_off_once(connection, caplog):
    caplog.set_level(logging.WARNING, logger="court_booker")
    store = history.History(connection)
    report = Reporter(store, clock=ticking_clock())
    connection.close()

    play_run(report)

    assert store.failed
    assert caplog.text.count("History database failed") == 1
    assert "Event sink failed" not in caplog.text
