"""Runner tests with a fake booker; no device required."""

import logging
from datetime import datetime, timedelta

import pytest

import court_booker.runner as runner
from court_booker.config import Config
from court_booker.errors import AppNotReadyError, NavigationError, SlotUnavailableError
from court_booker.events import EventKind, MemorySink, Reporter
from court_booker.screen import Node, Screen

FULL_SLOT = Node("18:00 - 19:00\nHết chỗ", (38, 1178, 263, 1262), True)


class FakeBooker:
    def __init__(self, device, config, report=None):
        self.booked = []
        self.events = []
        self.commands = 0
        self.last_screen = Screen([FULL_SLOT])

    def prepare(self):
        self.events.append("prepare")

    def locate_entry(self):
        self.events.append("locate")

    def book(self, slot, target, dry_run=False):
        if slot == "18:00 - 19:00":
            raise SlotUnavailableError("Slot 18:00 - 19:00 is fully booked")
        self.booked.append(slot)


class FakeDevice:
    def app_current(self):
        return {"package": "com.vinhomes.resident"}


def test_failed_round_does_not_stop_later_rounds(monkeypatch):
    monkeypatch.setattr(runner, "Booker", FakeBooker)
    config = Config(slots=["18:00 - 19:00", "19:00 - 20:00"])
    results = []

    returned = runner.run_booking(FakeDevice(), config, dry_run=True, results=results)

    assert returned is results
    assert [(r.slot, r.ok) for r in results] == [("18:00 - 19:00", False), ("19:00 - 20:00", True)]
    assert results[1].detail == "dry run passed"


def test_entry_is_located_just_before_the_start_time(monkeypatch):
    bookers = []

    def make_booker(device, config, report=None):
        bookers.append(FakeBooker(device, config, report))
        return bookers[-1]

    monkeypatch.setattr(runner, "Booker", make_booker)
    monkeypatch.setattr(
        runner, "wait_until", lambda target, offset: bookers[0].events.append(target)
    )
    start = datetime(2026, 10, 10, 6, 0)

    config = Config(slots=["19:00 - 20:00"], warm_up_seconds=60)
    runner.run_booking(FakeDevice(), config, start=start)

    assert bookers[0].events == [
        "prepare",
        start - timedelta(seconds=60),
        "locate",
        start - runner.LOCATE_AHEAD,
        "locate",
        start,
    ]


def test_failed_warm_up_is_retried_just_before_the_start(monkeypatch, caplog):
    class SlowListBooker(FakeBooker):
        def locate_entry(self):
            self.events.append("locate")
            if self.events.count("locate") == 1:
                raise NavigationError("Tapped 'Tiện ích' but the next screen did not appear")

    bookers = []

    def make_booker(device, config, report=None):
        bookers.append(SlowListBooker(device, config, report))
        return bookers[-1]

    monkeypatch.setattr(runner, "Booker", make_booker)
    monkeypatch.setattr(runner, "wait_until", lambda target, offset: None)

    results = runner.run_booking(
        FakeDevice(), Config(slots=["19:00 - 20:00"]), start=datetime(2026, 10, 10, 6, 0)
    )

    assert bookers[0].events == ["prepare", "locate", "locate"]
    assert results[0].ok
    assert "Could not open the utilities list yet" in caplog.text


def test_failed_round_logs_the_last_screen(monkeypatch, caplog):
    monkeypatch.setattr(runner, "Booker", FakeBooker)
    caplog.set_level(logging.DEBUG, logger="court_booker")
    config = Config(slots=["18:00 - 19:00", "19:00 - 20:00"])

    runner.run_booking(FakeDevice(), config, dry_run=True)

    messages = [record.getMessage() for record in caplog.records]
    error = messages.index("Slot 18:00 - 19:00 is fully booked")
    last_screen = (
        "Last screen read (1 elements):\n  [38,1178][263,1262] clickable '18:00 - 19:00\\nHết chỗ'"
    )
    assert messages[error + 1] == last_screen
    assert messages.count(last_screen) == 1


def test_failed_preparation_logs_the_last_screen(monkeypatch, caplog):
    class LoggedOutBooker(FakeBooker):
        def prepare(self):
            raise AppNotReadyError("The app did not show 'Tiện ích'")

    monkeypatch.setattr(runner, "Booker", LoggedOutBooker)
    caplog.set_level(logging.DEBUG, logger="court_booker")

    with pytest.raises(AppNotReadyError):
        runner.run_booking(FakeDevice(), Config(slots=["19:00 - 20:00"]))

    assert "Last screen read (1 elements):" in caplog.text


def test_events_follow_the_run(monkeypatch):
    monkeypatch.setattr(runner, "Booker", FakeBooker)
    sink = MemorySink()
    config = Config(slots=["18:00 - 19:00", "19:00 - 20:00"], days_ahead=2)

    runner.run_booking(FakeDevice(), config, dry_run=True, report=Reporter(sink))

    assert sink.kinds == [
        EventKind.APP_READY,
        EventKind.BOOKING_STARTED,
        EventKind.SLOT_STARTED,
        EventKind.SLOT_FAILED,
        EventKind.SLOT_STARTED,
        EventKind.SLOT_BOOKED,
    ]
    started, failed, booked = sink.events[1], sink.events[3], sink.events[5]
    assert started.data["court"] == config.court
    assert started.data["slots"] == ["18:00 - 19:00", "19:00 - 20:00"]
    assert started.data["dry_run"] is True
    assert sink.events[2].data == {"slot": "18:00 - 19:00", "round": 1, "rounds": 2}
    assert failed.data["reason"] == "Slot 18:00 - 19:00 is fully booked"
    assert booked.data["slot"] == "19:00 - 20:00"
    assert booked.data["commands"] == 0


def test_timed_run_reports_the_wait(monkeypatch):
    monkeypatch.setattr(runner, "Booker", FakeBooker)
    monkeypatch.setattr(runner, "wait_until", lambda target, offset: None)
    sink = MemorySink()
    start = datetime(2026, 10, 13, 6, 0)

    runner.run_booking(
        FakeDevice(), Config(slots=["19:00 - 20:00"]), start=start, report=Reporter(sink)
    )

    assert sink.kinds[:3] == [EventKind.APP_READY, EventKind.WAITING, EventKind.BOOKING_STARTED]
    assert sink.events[1].data == {"until": "2026-10-13T06:00:00"}
    assert sink.events[2].data["date"] == "2026-10-15"
