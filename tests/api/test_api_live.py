"""Tests for the live feed over a WebSocket."""

import pytest

from court_booker.api import live
from court_booker.api.activity import record
from court_booker.events import EventKind


@pytest.fixture(autouse=True)
def fast_poll(monkeypatch):
    monkeypatch.setattr(live, "POLL_SECONDS", 0.01)


def test_new_steps_are_pushed_as_runs_write_them(client, context, record_run):
    record_run(context.data.database)  # written before the client connects: not sent

    with client.websocket_connect("/api/live") as websocket:
        run_id = record_run(context.data.database, slots=[("18:00 - 19:00", True)])
        first = websocket.receive_json()
        kinds = [first["step"]["kind"]] + [
            websocket.receive_json()["step"]["kind"] for _ in range(4)
        ]

    assert first["type"] == "step"
    assert first["step"]["run_id"] == run_id
    assert kinds == [
        "run_started",
        "booking_started",
        "slot_started",
        "slot_booked",
        "run_finished",
    ]


def test_a_client_can_resume_after_a_step(client, context, record_run):
    record(context, EventKind.SETTINGS_SAVED, changed=["slots"])
    record(context, EventKind.SETTINGS_SAVED, changed=["court"])

    with client.websocket_connect("/api/live?after=1") as websocket:
        message = websocket.receive_json()

    assert message["step"]["id"] == 2
    assert message["step"]["data"] == {"changed": ["court"]}
