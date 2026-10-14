"""Tests for the history and activity routes."""

import pytest


@pytest.fixture
def database(context):
    return context.data.database


def test_no_runs_yet(client):
    assert client.get("/api/runs").json() == []


def test_runs_are_listed_newest_first(client, database, record_run):
    first = record_run(database, slots=[("18:00 - 19:00", True), ("19:00 - 20:00", False)])
    second = record_run(database, trigger="dry_run")

    runs = client.get("/api/runs").json()

    assert [run["id"] for run in runs] == [second, first]
    assert runs[1]["booked"] == 1
    assert runs[1]["total"] == 2
    assert runs[1]["play_date"] == "2026-10-15"
    assert [(slot["slot"], slot["ok"]) for slot in runs[1]["slots"]] == [
        ("18:00 - 19:00", True),
        ("19:00 - 20:00", False),
    ]


def test_runs_filter_and_page(client, database, record_run):
    ids = [record_run(database, date=f"2026-10-{day}") for day in (13, 14, 15)]
    record_run(database, date="2026-11-01")

    october = client.get("/api/runs", params={"month": "2026-10", "limit": 2}).json()
    older = client.get("/api/runs", params={"month": "2026-10", "before": october[-1]["id"]})

    assert [run["id"] for run in october] == [ids[2], ids[1]]
    assert [run["id"] for run in older.json()] == [ids[0]]


@pytest.mark.parametrize(
    "params", [{"month": "October"}, {"trigger": "nightly"}, {"limit": 0}, {"limit": 501}]
)
def test_bad_run_filters_are_refused(client, params):
    assert client.get("/api/runs", params=params).status_code == 422


def test_one_run_in_full(client, database, record_run):
    run_id = record_run(database, slots=[("18:00 - 19:00", True)])

    run = client.get(f"/api/runs/{run_id}").json()

    assert run["slots"] == [
        {
            "slot": "18:00 - 19:00",
            "ok": True,
            "reason": None,
            "finished_at": run["slots"][0]["finished_at"],
            "seconds": 7.8,
            "commands": 51,
        }
    ]
    assert [step["kind"] for step in run["steps"]] == [
        "run_started",
        "booking_started",
        "slot_started",
        "slot_booked",
        "run_finished",
    ]
    assert run["log_lines"] == []


def test_an_unknown_run_is_not_found(client):
    response = client.get("/api/runs/42")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "No run 42"}


def test_activity_is_listed_newest_first_by_category(client, database, record_run):
    run_id = record_run(database, slots=[("18:00 - 19:00", False)])

    everything = client.get("/api/events").json()
    errors = client.get("/api/events", params={"category": "error"}).json()

    assert everything[0]["kind"] == "run_finished"
    assert {step["run_id"] for step in everything} == {run_id}
    assert [(step["kind"], step["data"]["reason"]) for step in errors] == [
        ("slot_failed", "fully booked")
    ]


def test_activity_pages_back(client, database, record_run):
    record_run(database)
    (newest,) = client.get("/api/events", params={"limit": 1}).json()

    (older,) = client.get("/api/events", params={"limit": 1, "before": newest["id"]}).json()

    assert older["id"] < newest["id"]


def test_an_unknown_category_is_refused(client):
    assert client.get("/api/events", params={"category": "misc"}).status_code == 422
