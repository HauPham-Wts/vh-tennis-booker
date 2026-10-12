"""Runner tests with a fake booker; no device required."""

import logging
from datetime import datetime

import pytest

import court_booker.runner as runner
from court_booker.config import Config
from court_booker.errors import AppNotReadyError, SlotUnavailableError
from court_booker.screen import Node, Screen

FULL_SLOT = Node("18:00 - 19:00\nHết chỗ", (38, 1178, 263, 1262), True)


class FakeBooker:
    def __init__(self, device, config):
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

    def make_booker(device, config):
        bookers.append(FakeBooker(device, config))
        return bookers[-1]

    monkeypatch.setattr(runner, "Booker", make_booker)
    monkeypatch.setattr(
        runner, "wait_until", lambda target, offset: bookers[0].events.append(target)
    )
    start = datetime(2026, 10, 10, 6, 0)

    runner.run_booking(FakeDevice(), Config(slots=["19:00 - 20:00"]), start=start)

    assert bookers[0].events == ["prepare", start - runner.LOCATE_AHEAD, "locate", start]


def test_failed_round_logs_the_last_screen(monkeypatch, caplog):
    monkeypatch.setattr(runner, "Booker", FakeBooker)
    caplog.set_level(logging.DEBUG, logger="court_booker")
    config = Config(slots=["18:00 - 19:00", "19:00 - 20:00"])

    runner.run_booking(FakeDevice(), config, dry_run=True)

    messages = [record.getMessage() for record in caplog.records]
    error = messages.index("Slot 18:00 - 19:00 is fully booked")
    assert messages[error + 1 : error + 3] == [
        "Last screen read (1 elements):",
        "  [38,1178][263,1262] clickable '18:00 - 19:00\\nHết chỗ'",
    ]
    assert messages.count("Last screen read (1 elements):") == 1


def test_failed_preparation_logs_the_last_screen(monkeypatch, caplog):
    class LoggedOutBooker(FakeBooker):
        def prepare(self):
            raise AppNotReadyError("The app did not show 'Tiện ích'")

    monkeypatch.setattr(runner, "Booker", LoggedOutBooker)
    caplog.set_level(logging.DEBUG, logger="court_booker")

    with pytest.raises(AppNotReadyError):
        runner.run_booking(FakeDevice(), Config(slots=["19:00 - 20:00"]))

    assert "Last screen read (1 elements):" in caplog.text
