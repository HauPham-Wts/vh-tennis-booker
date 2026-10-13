"""Tests for reading the history back."""

import sqlite3

import pytest

from court_booker import history, history_read


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


def test_runs_come_newest_first_with_their_slot_counts(path, read, record_run):
    first = record_run(
        path, slots=[("18:00 - 19:00", True), ("19:00 - 20:00", False)], status="partial"
    )
    second = record_run(path, trigger="dry_run", slots=[("10:00 - 11:00", True)])

    runs = history_read.list_runs(read())

    assert [run["id"] for run in runs] == [second, first]
    assert runs[0]["dry_run"] is True
    assert (runs[1]["booked"], runs[1]["total"], runs[1]["status"]) == (1, 2, "partial")
    assert runs[1]["court"] == "S6 - Sân tennis"


def test_runs_filter_by_play_month_and_trigger(path, read, record_run):
    october = record_run(path, date="2026-10-31")
    record_run(path, date="2026-11-01")
    record_run(path, trigger="dry_run", date="2026-10-15")

    assert [
        r["id"] for r in history_read.list_runs(read(), month="2026-10", trigger="scheduled")
    ] == [october]


def test_runs_page_back_from_a_run(path, read, record_run):
    ids = [record_run(path) for _ in range(5)]

    page = history_read.list_runs(read(), before=ids[3], limit=2)

    assert [run["id"] for run in page] == [ids[2], ids[1]]


def test_one_run_comes_with_slots_steps_and_log_lines(path, read, record_run):
    run_id = record_run(path, slots=[("18:00 - 19:00", True), ("19:00 - 20:00", False)])

    run = history_read.get_run(read(), run_id)

    assert [(slot["slot"], slot["ok"], slot["reason"]) for slot in run["slots"]] == [
        ("18:00 - 19:00", True, None),
        ("19:00 - 20:00", False, "fully booked"),
    ]
    assert [step["kind"] for step in run["steps"]][:2] == ["run_started", "booking_started"]
    assert run["steps"][1]["data"]["court"] == "S6 - Sân tennis"
    assert run["log_lines"] == []  # the sink alone logs nothing


def test_an_unknown_run_is_none(path, read, record_run):
    assert history_read.get_run(read(), 42) is None


def test_activity_comes_newest_first_and_filters_by_category(path, read, record_run):
    record_run(path, slots=[("18:00 - 19:00", False)])

    steps = history_read.list_events(read())
    errors = history_read.list_events(read(), category="error")

    assert steps[0]["kind"] == "run_finished"
    assert steps[-1]["kind"] == "run_started"
    assert [step["kind"] for step in errors] == ["slot_failed"]
    assert errors[0]["data"]["reason"] == "fully booked"


def test_activity_pages_back(path, read, record_run):
    record_run(path)
    newest = history_read.list_events(read(), limit=1)

    older = history_read.list_events(read(), before=newest[0]["id"], limit=1)

    assert older[0]["id"] == newest[0]["id"] - 1


def test_a_passed_dry_run_is_found(path, read, record_run):
    record_run(path, trigger="dry_run", status="failed")
    record_run(path, trigger="scheduled", status="ok")
    assert not history_read.dry_run_passed(read())

    record_run(path, trigger="dry_run", status="ok")
    assert history_read.dry_run_passed(read())
