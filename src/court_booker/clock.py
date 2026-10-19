"""Exact start time: parse it, tell the true time and wait for it."""

from __future__ import annotations

import logging
import socket
import struct
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from datetime import time as time_of_day
from typing import Callable, NamedTuple

from court_booker.errors import RequestError

logger = logging.getLogger(__name__)

LATE_START_GRACE = timedelta(minutes=10)
"""A start time missed by less than this (e.g. the PC woke late) still runs at once."""
NTP_FALLBACKS = ("time.google.com", "time.windows.com", "pool.ntp.org")
"""Servers asked in turn when the configured one does not answer (time.google.com timed
out once, 2026-10-15)."""

_TIME_FORMATS = ("%H:%M:%S", "%H:%M")
_NTP_PORT = 123
_NTP_TIMEOUT = 1.0
_NTP_ATTEMPTS = 2
_NTP_SAMPLES = 4
"""Answers asked of a server per check; the one with the shortest round trip is kept.

A check that took 0.57 s read the PC clock 0.531 s fast; quick ones (40-65 ms) from three
servers read 0.413 s minutes later, within 2 ms of each other (2026-10-19)."""
_NTP_EPOCH_OFFSET = 2_208_988_800  # seconds from 1900-01-01 to 1970-01-01
_NTP_PACKET_SIZE = 48
_NTP_SERVER_MODE = 4
_NTP_MAX_STRATUM = 15
_COARSE_STEP = 30.0
_FINE_WINDOW = 1.0
_FINE_STEP = 0.001


def resolve_start(text: str, now: datetime, grace: timedelta = LATE_START_GRACE) -> datetime:
    """Return today's ``HH:MM[:SS]`` as a datetime.

    A time passed by less than ``grace`` is returned as is (the wait then ends at
    once); a later one raises ``RequestError``.
    """
    start = datetime.combine(now.date(), parse_time(text, "start time"))
    if start < now:
        late = now - start
        if late > grace:
            raise RequestError(f"Start time {start:%H:%M:%S} has already passed today")
        logger.warning("Started %.0f s after %s; booking now", late.total_seconds(), text)
    return start


def parse_time(text: str, name: str) -> time_of_day:
    """Return ``HH:MM`` or ``HH:MM:SS`` as a time; ``name`` labels the error."""
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise RequestError(f"Invalid {name} {text!r}; use HH:MM or HH:MM:SS")


class NtpSample(NamedTuple):
    """One answer of a time server."""

    offset: float
    """Seconds to add to the local clock to match the server's."""
    delay: float
    """Round trip less the server's own time; the offset is off by half of it at most."""


def _udp_socket() -> socket.socket:
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def query_ntp(
    server: str,
    timeout: float = _NTP_TIMEOUT,
    open_socket: Callable[[], socket.socket] = _udp_socket,
    resolve: Callable[[str], str] = socket.gethostbyname,
) -> NtpSample | None:
    """Ask ``server`` once; return its answer, or ``None`` with the reason logged.

    The name is resolved before the exchange is timed: a DNS lookup inside it would count as
    time on the way out and shift the offset by half of it.
    """
    request = b"\x1b" + bytes(_NTP_PACKET_SIZE - 1)  # version 3, client mode
    try:
        address = resolve(server)
        with open_socket() as sock:
            sock.settimeout(timeout)
            sent = time.time()
            sock.sendto(request, (address, _NTP_PORT))
            reply, _ = sock.recvfrom(_NTP_PACKET_SIZE)
            received = time.time()
    except OSError as exc:
        logger.info("Clock check against %s failed (%s)", server, str(exc) or type(exc).__name__)
        return None
    sample = read_reply(reply, sent, received)
    if sample is None:
        logger.info("Invalid reply from %s", server)
    return sample


def ntp_offset(
    server: str,
    fallbacks: Sequence[str] = NTP_FALLBACKS,
    attempts: int = _NTP_ATTEMPTS,
    samples: int = _NTP_SAMPLES,
    query: Callable[[str], NtpSample | None] = query_ntp,
) -> float | None:
    """Return seconds to add to the local clock to match NTP time, or ``None``.

    Asks ``server``, then each fallback not asked yet, and stops at the first that answers:
    ``samples`` times, or until ``attempts`` questions failed, keeping the answer with the
    shortest round trip, whose offset is the most accurate. A run measures it before
    waiting for the start time, so the seconds lost when every server fails cost no
    booking time.
    """
    servers = list(dict.fromkeys([server, *fallbacks]))
    for name in servers:
        answers: list[NtpSample] = []
        failed = 0
        while len(answers) < samples and failed < attempts:
            sample = query(name)
            if sample is None:
                failed += 1
            else:
                answers.append(sample)
        if answers:
            best = min(answers, key=lambda answer: answer.delay)
            logger.info(
                "Clock checked against %s: round trip %.0f ms (best of %d)",
                name,
                best.delay * 1000,
                len(answers),
            )
            return best.offset
    logger.warning("No time server answered (%s)", ", ".join(servers))
    return None


class NtpClock:
    """The time a timed run waits by: NTP time carried forward on a counter nothing sets.

    Windows Time sets the PC clock on its own schedule, also while a run waits: on
    2026-10-19 it synchronised at 05:50:21, 18 s after the run had measured the PC clock
    0.757 s slow, and slewed that error away (Windows slews an error under 1 s rather than
    stepping it), so the run still added 0.757 s at 06:00 and tapped up to 0.76 s early.
    Each answer of the time server therefore anchors this clock: the NTP time then, carried
    forward by :func:`time.perf_counter` (QueryPerformanceCounter on Windows), which no
    clock setting moves. Without an answer the clock is the PC clock, which Windows then
    keeps right.
    """

    def __init__(
        self,
        server: str = "",
        measure: Callable[[str], float | None] = ntp_offset,
        local_now: Callable[[], datetime] = datetime.now,
        counter: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.server = server
        """Time server :meth:`measure` asks; empty never asks (``ntp_server = ""``)."""
        self.offset: float | None = None
        """Seconds the PC clock was behind NTP time at the last answer; ``None`` before one."""
        self._measure = measure
        self._local_now = local_now
        self._counter = counter
        self._anchor: tuple[datetime, float] | None = None
        self._checked_at = ""
        """PC clock time of the last answer, as the log line of it shows."""

    def measure(self) -> None:
        """Ask the time server and anchor the clock to its answer.

        A later answer anchors it again and logs how far the PC clock and the anchored time
        moved since the answer before; no answer keeps the anchor there is.
        """
        if not self.server:
            return
        offset = self._measure(self.server)
        if offset is None:
            if self.offset is None:
                logger.info("Using the PC clock")
            else:
                logger.info(
                    "Keeping the clock offset %+.3f s from %s", self.offset, self._checked_at
                )
            return
        counter = self._counter()
        local = self._local_now()
        true_now = local + timedelta(seconds=offset)
        if self.offset is None:
            logger.info("Clock offset %+.3f s", offset)
        else:
            logger.info(
                "Clock offset %+.3f s (%+.3f s since %s; anchored time off by %+.3f s)",
                offset,
                offset - self.offset,
                self._checked_at,
                (self._anchored(counter) - true_now).total_seconds(),
            )
        self._anchor = (true_now, counter)
        self._checked_at = format_time(local)
        self.offset = offset

    def now(self) -> datetime:
        """Return the time carried forward from the last answer, else the PC clock's."""
        if self._anchor is None:
            return self._local_now()
        return self._anchored(self._counter())

    def reading(self) -> str:
        """Return the time now for the log: the anchored time and the PC clock's, or the latter."""
        if self._anchor is None:
            return f"{format_time(self._local_now())} (PC clock)"
        return f"{format_time(self.now())} (NTP), PC clock {format_time(self._local_now())}"

    def _anchored(self, counter: float) -> datetime:
        assert self._anchor is not None
        moment, anchored_at = self._anchor
        return moment + timedelta(seconds=counter - anchored_at)


def format_time(moment: datetime) -> str:
    """Return the time of day of ``moment`` to the millisecond, e.g. ``06:00:00.100``."""
    return moment.time().isoformat(timespec="milliseconds")


def read_reply(reply: bytes, sent: float, received: float) -> NtpSample | None:
    """Return the answer in an NTP reply, given the local send and receive times.

    ``None`` for a reply that is short, not from a server, or from a server that is not
    synchronised (stratum 0, as in a refusal), whose timestamps are not the time.
    """
    if len(reply) < _NTP_PACKET_SIZE:
        return None
    if reply[0] & 0x07 != _NTP_SERVER_MODE or not 1 <= reply[1] <= _NTP_MAX_STRATUM:
        return None
    server_received = _ntp_timestamp(reply, 32)
    server_sent = _ntp_timestamp(reply, 40)
    return NtpSample(
        offset=((server_received - sent) + (server_sent - received)) / 2,
        delay=(received - sent) - (server_sent - server_received),
    )


def wait_until(
    target: datetime,
    now: Callable[[], datetime] = datetime.now,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Block until ``now()`` (such as :meth:`NtpClock.now`) reaches ``target``.

    Sleeps in long steps first, then in millisecond steps for the last second, so
    the start is late by about a millisecond at most.
    """
    remaining = _remaining(target, now)
    if remaining > 0:
        logger.info("Waiting %.1f s until %s", remaining, format_time(target))
    while remaining > 0:
        if remaining > _FINE_WINDOW:
            sleep(min(remaining - _FINE_WINDOW, _COARSE_STEP))
        else:
            sleep(min(remaining, _FINE_STEP))
        remaining = _remaining(target, now)


def _remaining(target: datetime, now: Callable[[], datetime]) -> float:
    return (target - now()).total_seconds()


def _ntp_timestamp(packet: bytes, position: int) -> float:
    seconds, fraction = struct.unpack("!II", packet[position : position + 8])
    return seconds - _NTP_EPOCH_OFFSET + fraction / 2**32
