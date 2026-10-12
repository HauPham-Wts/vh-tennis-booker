"""Tests for run events and their sinks."""

import logging
from datetime import datetime

from court_booker.events import (
    Event,
    EventKind,
    LogSink,
    MemorySink,
    MultiSink,
    NullSink,
    Reporter,
)

NOW = datetime(2026, 10, 13, 6, 0, 6)


def test_reporter_stamps_the_time_and_passes_the_data():
    sink = MemorySink()
    report = Reporter(sink, clock=lambda: NOW)

    report(EventKind.SLOT_BOOKED, slot="18:00 - 19:00", seconds=7.0)

    assert sink.events == [
        Event(EventKind.SLOT_BOOKED, NOW, {"slot": "18:00 - 19:00", "seconds": 7.0})
    ]
    assert sink.kinds == [EventKind.SLOT_BOOKED]


def test_reporter_without_sink_drops_events():
    report = Reporter()

    report(EventKind.APP_READY)

    assert isinstance(report.sink, NullSink)


def test_failing_sink_is_logged_not_raised(caplog):
    class BrokenSink:
        def emit(self, event):
            raise OSError("disk full")

    report = Reporter(BrokenSink(), clock=lambda: NOW)

    report(EventKind.APP_READY)

    assert "Event sink failed on app_ready" in caplog.text


def test_multi_sink_hands_each_event_to_every_sink():
    first, second = MemorySink(), MemorySink()
    report = Reporter(MultiSink(first, second), clock=lambda: NOW)

    report(EventKind.WAITING, until="06:00:00")

    assert first.events == second.events
    assert first.kinds == [EventKind.WAITING]


def test_log_sink_writes_one_debug_line(caplog):
    caplog.set_level(logging.DEBUG, logger="court_booker")

    LogSink().emit(Event(EventKind.SLOT_FAILED, NOW, {"slot": "19:00 - 20:00", "seconds": 1.0}))

    assert "Event slot_failed slot='19:00 - 20:00' seconds=1.0" in caplog.text


def test_kind_values_are_stable_strings():
    assert EventKind.RUN_STARTED.value == "run_started"
    assert EventKind("slot_booked") is EventKind.SLOT_BOOKED
