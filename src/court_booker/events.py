"""Progress events of a booking run.

Beside its log lines, the engine reports what it does as events with fixed fields, so other
parts can follow a run without parsing log text: the log today, later the history database
and the live view of the app. Event data holds only JSON-friendly values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


class EventKind(str, Enum):
    """What happened. The value is stable: it becomes a database value and a message key."""

    # The whole run.
    RUN_STARTED = "run_started"
    DEVICE_READY = "device_ready"
    APP_READY = "app_ready"
    WAITING = "waiting"
    BOOKING_STARTED = "booking_started"
    RUN_FINISHED = "run_finished"
    # One round, i.e. one slot.
    SLOT_STARTED = "slot_started"
    CALENDAR_OPENED = "calendar_opened"
    DATE_SELECTED = "date_selected"
    SLOT_SELECTED = "slot_selected"
    COURT_SELECTED = "court_selected"
    TERMS_ACCEPTED = "terms_accepted"
    SLOT_BOOKED = "slot_booked"
    SLOT_FAILED = "slot_failed"
    # The run lock.
    LOCK_CLEARED = "lock_cleared"
    LOCK_WAITING = "lock_waiting"
    LOCK_TAKEN_OVER = "lock_taken_over"


@dataclass(frozen=True)
class Event:
    """One step of a run: its kind, when it happened and its details."""

    kind: EventKind
    time: datetime
    data: dict[str, Any] = field(default_factory=dict)


class EventSink(Protocol):
    """Receives every event of a run."""

    def emit(self, event: Event) -> None: ...


class NullSink:
    """Drop every event."""

    def emit(self, event: Event) -> None:
        pass


class MemorySink:
    """Keep events in a list, for tests."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)

    @property
    def kinds(self) -> list[EventKind]:
        """Return the kind of every event received, in order."""
        return [event.kind for event in self.events]


class LogSink:
    """Write each event as one debug line, next to the existing log lines."""

    def emit(self, event: Event) -> None:
        details = " ".join(f"{key}={value!r}" for key, value in event.data.items())
        logger.debug("Event %s %s", event.kind.value, details)


class MultiSink:
    """Hand every event to several sinks, in order."""

    def __init__(self, *sinks: EventSink) -> None:
        self.sinks = sinks

    def emit(self, event: Event) -> None:
        for sink in self.sinks:
            sink.emit(event)


class Reporter:
    """Stamp events with the time and hand them to a sink.

    A failing sink is logged and otherwise ignored: reporting must never cost a booking.
    """

    def __init__(
        self, sink: EventSink | None = None, clock: Callable[[], datetime] = datetime.now
    ) -> None:
        self.sink: EventSink = sink if sink is not None else NullSink()
        self._clock = clock

    def __call__(self, kind: EventKind, **data: Any) -> None:
        event = Event(kind, self._clock(), data)
        try:
            self.sink.emit(event)
        except Exception:  # a broken sink must not stop the run
            logger.warning("Event sink failed on %s", kind.value, exc_info=True)
