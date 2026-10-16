"""Runner tests with a fake booker; no device required."""

import logging
import threading
from datetime import datetime, timedelta

import pytest

import court_booker.runner as runner
from court_booker.config import Config
from court_booker.errors import (
    AppNotReadyError,
    DeviceNotRespondingError,
    NavigationError,
    SlotUnavailableError,
)
from court_booker.events import EventKind, MemorySink, Reporter
from court_booker.flow import Booked
from court_booker.screen import Node, Screen
from court_booker.watchdog import GuardedDevice, Watchdog

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
        return Booked(shown_court="S9 - Sân tennis")


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
    assert booked.data["shown_court"] == "S9 - Sân tennis"
    assert "ticket" not in booked.data  # details not found are left out


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


def test_a_frozen_device_ends_the_run_after_its_round(monkeypatch):
    class FrozenBooker(FakeBooker):
        def book(self, slot, target, dry_run=False):
            raise DeviceNotRespondingError("MuMu did not answer dump_hierarchy within 60 s")

    monkeypatch.setattr(runner, "Booker", FrozenBooker)
    sink = MemorySink()
    results = []
    config = Config(slots=["18:00 - 19:00", "19:00 - 20:00"])

    with pytest.raises(DeviceNotRespondingError):
        runner.run_booking(FakeDevice(), config, results=results, report=Reporter(sink))

    assert [(r.slot, r.ok) for r in results] == [("18:00 - 19:00", False)]
    assert sink.kinds[-1] is EventKind.SLOT_FAILED
    assert sink.events[-1].data["reason"] == "MuMu did not answer dump_hierarchy within 60 s"


class TouchDevice:
    """Record taps the way uiautomator2 takes them: ``touch.down(x, y).up(x, y)``."""

    serial = "127.0.0.1:16384"

    def __init__(self, release=None):
        self.events = []
        self.touch = self
        self.release = release
        """An event ``up`` waits for, to stand for a frozen emulator."""

    def down(self, x, y):
        self.events.append(("down", x, y))
        return self

    def up(self, x, y):
        if self.release is not None:
            self.release.wait()
        self.events.append(("up", x, y))
        return self

    def click(self, x, y):
        self.events.append(("click", x, y))

    def press(self, key):
        self.events.append(("press", key))
        return True


def test_quick_tap_touches_down_then_up_at_the_point():
    device = TouchDevice()

    runner.QuickTap(device).click(270, 1537)

    assert device.events == [("down", 270, 1537), ("up", 270, 1537)]


def test_quick_tap_passes_everything_else_to_the_device():
    device = TouchDevice()
    quick = runner.QuickTap(device)

    assert quick.press("back") is True
    assert quick.serial == "127.0.0.1:16384"
    assert device.events == [("press", "back")]


def test_a_quick_tap_is_one_time_limited_call():
    release = threading.Event()
    device = GuardedDevice(runner.QuickTap(TouchDevice(release)), Watchdog(timeout=0.05))
    try:
        with pytest.raises(DeviceNotRespondingError, match="did not answer click within"):
            device.click(270, 1537)
    finally:
        release.set()
