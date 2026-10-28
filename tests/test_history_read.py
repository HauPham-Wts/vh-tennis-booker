"""Tests for reading the history back."""

import sqlite3

import pytest

from court_booker import history, history_read
from court_booker.events import EventKind, Reporter


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


def test_runs_come_with_their_slots_in_order(path, read, record_run):
    first = record_run(
        path, slots=[("18:00 - 19:00", True), ("19:00 - 20:00", False)], status="partial"
    )
    record_run(path, date=None)
    third = record_run(path, slots=[("06:00 - 07:00", True)])

    runs = {run["id"]: run for run in history_read.list_runs(read())}

    assert [(slot["slot"], slot["ok"]) for slot in runs[first]["slots"]] == [
        ("18:00 - 19:00", True),
        ("19:00 - 20:00", False),
    ]
    assert runs[first]["slots"][1]["reason"] == "fully booked"
    assert "run_id" not in runs[first]["slots"][0]
    assert [slot["slot"] for slot in runs[third]["slots"]] == ["06:00 - 07:00"]
    assert [run["slots"] for run in runs.values() if run["id"] not in (first, third)] == [[]]


def test_runs_read_their_slots_in_one_query(path, read, record_run):
    for _ in range(5):
        record_run(path, slots=[("18:00 - 19:00", True)])
    connection = read()
    statements = []
    connection.set_trace_callback(statements.append)

    history_read.list_runs(connection)

    assert len(statements) == 2


def test_runs_filter_by_play_month_and_trigger(path, read, record_run):
    october = record_run(path, date="2026-10-31")
    record_run(path, date="2026-11-01")
    record_run(path, trigger="dry_run", date="2026-10-15")

    assert [
        r["id"] for r in history_read.list_runs(read(), month="2026-10", trigger="scheduled")
    ] == [october]


def test_runs_filter_by_dry_run_not_by_trigger(path, read, record_run):
    real = record_run(path, slots=[("18:00 - 19:00", True)])
    manual = record_run(path, trigger="manual")
    dry = record_run(path, trigger="dry_run")
    scheduled_test = record_run(path, dry_run=True)

    def ids(**filters):
        return [run["id"] for run in history_read.list_runs(read(), **filters)]

    assert ids(dry_run=False) == [manual, real]
    assert ids(dry_run=True) == [scheduled_test, dry]
    assert ids() == [scheduled_test, dry, manual, real]


def test_months_count_the_runs_and_slots_of_real_bookings(path, read, record_run):
    record_run(path, date="2026-10-15", slots=[("18:00 - 19:00", True), ("19:00 - 20:00", True)])
    record_run(path, date="2026-10-31", slots=[("18:00 - 19:00", False)], status="failed")
    record_run(path, date="2026-11-01", slots=[("06:00 - 07:00", True)])
    record_run(path, trigger="dry_run", date="2026-10-16", slots=[("10:00 - 11:00", True)])
    record_run(path, dry_run=True, date="2026-09-30", slots=[("10:00 - 11:00", True)])
    record_run(path, date=None)

    assert history_read.list_months(read()) == [
        {"month": "2026-11", "runs": 1, "booked": 1},
        {"month": "2026-10", "runs": 2, "booked": 2},
    ]


def test_no_months_without_bookings(path, read):
    assert history_read.list_months(read()) == []


def test_runs_page_back_from_a_run(path, read, record_run):
    ids = [record_run(path) for _ in range(5)]

    page = history_read.list_runs(read(), before=ids[3], limit=2)

    assert [run["id"] for run in page] == [ids[2], ids[1]]


def test_runs_of_the_newest_days_come_whole(path, read, record_run):
    oldest = record_run(path, day="2026-10-10")
    middle = [record_run(path, day="2026-10-12") for _ in range(2)]
    newest = record_run(path, day="2026-10-14")
    tested = record_run(path, trigger="dry_run", day="2026-10-15")

    def ids(**filters):
        return [run["id"] for run in history_read.list_runs(read(), **filters)]

    assert ids(days=2) == [tested, newest]
    assert ids(days=2, dry_run=False) == [newest, *reversed(middle)]
    assert ids(days=2, dry_run=False, before=middle[1]) == [middle[0], oldest]
    assert ids(days=9) == [tested, newest, *reversed(middle), oldest]
    assert ids(days=1, dry_run=False, limit=1) == [newest]


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


def test_the_last_setup_result_is_read(path, read):
    assert history_read.last_setup(read()) is None
    store = history.History(history.connect(path))
    report = Reporter(store)
    report(EventKind.SETUP_FINISHED, left=["wake_timers"], error=None)
    report(EventKind.SETUP_FINISHED, left=[], error=None)
    store.close()

    last = history_read.last_setup(read())

    assert last["left"] == []
    assert last["checked_at"].startswith("20")


def test_steps_after_a_step_come_oldest_first(path, read, record_run):
    assert history_read.last_event_id(read()) == 0
    record_run(path)
    newest = history_read.last_event_id(read())
    record_run(path, slots=[("18:00 - 19:00", True)])

    later = history_read.events_after(read(), newest)

    assert later[0]["kind"] == "run_started"
    assert later[-1]["kind"] == "run_finished"
    assert [step["id"] for step in later] == sorted(step["id"] for step in later)
    assert history_read.events_after(read(), newest, limit=2)[1]["id"] == newest + 2


def test_each_instance_comes_with_the_subdivision_it_told_last(path, read):
    for device, subdivision in [(0, "origami"), (1, "bs"), (0, "bs")]:
        store = history.History(history.connect(path))
        report = Reporter(store)
        report(
            EventKind.RUN_STARTED, trigger="dry_run", dry_run=True, version="0.16.0", device=device
        )
        report(EventKind.ACCOUNT_SUBDIVISION, subdivision=subdivision)
        store.close()

    found = history_read.account_subdivisions(read())

    assert [(item["device"], item["subdivision"]) for item in found] == [(0, "bs"), (1, "bs")]
    assert all(item["seen_at"].startswith("20") for item in found)
