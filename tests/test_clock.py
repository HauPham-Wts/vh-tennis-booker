"""Start-time tests with fake clocks; no network required."""

import logging
import socket
import struct
import time
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import court_booker.clock as clock_module
from court_booker.clock import (
    NtpClock,
    NtpSample,
    ntp_offset,
    query_ntp,
    read_reply,
    resolve_start,
    wait_until,
)
from court_booker.errors import RequestError

NOW = datetime(2026, 10, 8, 5, 45, 0)


def test_resolve_start_later_today():
    assert resolve_start("06:00", NOW) == datetime(2026, 10, 8, 6, 0, 0)
    assert resolve_start("06:00:30", NOW) == datetime(2026, 10, 8, 6, 0, 30)


def test_resolve_start_slightly_late_still_runs():
    assert resolve_start("05:40", NOW) == datetime(2026, 10, 8, 5, 40)


def test_resolve_start_long_passed_is_rejected():
    with pytest.raises(RequestError, match="already passed"):
        resolve_start("05:00", NOW)


@pytest.mark.parametrize("text", ["6h", "25:00", "06:00 AM", ""])
def test_resolve_start_rejects_bad_format(text):
    with pytest.raises(RequestError, match="Invalid start time"):
        resolve_start(text, NOW)


class FakeClock:
    def __init__(self, start):
        self.now_value = start
        self.sleeps = []

    def now(self):
        return self.now_value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now_value += timedelta(seconds=seconds)


def test_wait_until_ends_on_time_with_fine_steps_at_the_end():
    clock = FakeClock(NOW)
    target = datetime(2026, 10, 8, 6, 0)

    wait_until(target, now=clock.now, sleep=clock.sleep)

    assert clock.now_value >= target
    assert clock.now_value - target < timedelta(milliseconds=2)
    assert max(clock.sleeps) <= 30
    assert clock.sleeps[-1] <= 0.001


def test_wait_until_past_target_returns_at_once():
    clock = FakeClock(NOW)
    wait_until(NOW - timedelta(minutes=1), now=clock.now, sleep=clock.sleep)
    assert clock.sleeps == []


def ntp_reply(server_seconds, mode=4, stratum=2):
    seconds = int(server_seconds) + 2_208_988_800
    fraction = int((server_seconds % 1) * 2**32)
    timestamp = struct.pack("!II", seconds, fraction)
    return bytes([0x18 | mode, stratum]) + bytes(30) + timestamp + timestamp  # version 3


def test_read_reply():
    # Sent at 1000.0, received at 1000.2; the server stamped 1001.6 in the middle.
    sample = read_reply(ntp_reply(1001.6), sent=1000.0, received=1000.2)
    assert sample.offset == pytest.approx(1.5, abs=1e-6)
    assert sample.delay == pytest.approx(0.2, abs=1e-6)


def test_read_short_reply_is_none():
    assert read_reply(b"\x00" * 10, 0.0, 0.0) is None


@pytest.mark.parametrize(
    ("mode", "stratum"),
    [(3, 2), (4, 0), (4, 16)],  # a client's packet, a refusal, a server without a clock
)
def test_read_reply_without_the_time_is_none(mode, stratum):
    assert read_reply(ntp_reply(1001.6, mode, stratum), 1000.0, 1000.2) is None


class FakeSocket:
    """One UDP exchange; ``answer`` is the reply or the error ``recvfrom`` raises."""

    def __init__(self, answer):
        self.answer = answer
        self.timeout = None
        self.addresses = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def settimeout(self, seconds):
        self.timeout = seconds

    def sendto(self, data, address):
        self.addresses.append(address)

    def recvfrom(self, size):
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer, ("192.0.2.1", 123)


def resolve(server):
    """Stand in for DNS: tests never touch the network."""
    return "192.0.2.1"


def test_query_ntp_returns_the_answer_in_a_reply():
    sock = FakeSocket(ntp_reply(time.time() + 1.5))

    sample = query_ntp("time.google.com", open_socket=lambda: sock, resolve=resolve)

    assert sample.offset == pytest.approx(1.5, abs=0.5)
    assert sock.addresses == [("192.0.2.1", 123)]
    assert sock.timeout == 1.0


def test_query_ntp_resolves_the_name_before_timing_the_exchange(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(clock_module, "time", SimpleNamespace(time=lambda: now[0]))

    def slow_resolve(server):
        now[0] += 0.3  # a slow DNS answer, on the way out only
        return "192.0.2.1"

    sock = FakeSocket(ntp_reply(1001.5))
    sample = query_ntp("time.google.com", open_socket=lambda: sock, resolve=slow_resolve)

    # Timed with the lookup inside, the offset would read 1.35 s and the round trip 0.3 s.
    assert sample == (pytest.approx(1.2), 0.0)


def test_query_ntp_logs_a_name_that_does_not_resolve(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")

    def no_dns(server):
        raise socket.gaierror(11001, "getaddrinfo failed")

    assert query_ntp("time.google.com", resolve=no_dns) is None
    assert "Clock check against time.google.com failed ([Errno 11001] getaddrinfo" in caplog.text


@pytest.mark.parametrize(
    ("answer", "logged"),
    [
        (socket.timeout("timed out"), "Clock check against time.google.com failed (timed out)"),
        (TimeoutError(), "Clock check against time.google.com failed (TimeoutError)"),
        (b"\x00" * 10, "Invalid reply from time.google.com"),
        (ntp_reply(1001.6, stratum=0), "Invalid reply from time.google.com"),
    ],
)
def test_query_ntp_logs_why_it_has_no_offset(answer, logged, caplog):
    caplog.set_level(logging.INFO, logger="court_booker")

    sock = FakeSocket(answer)
    assert query_ntp("time.google.com", open_socket=lambda: sock, resolve=resolve) is None
    assert logged in caplog.text


def test_ntp_offset_leaves_a_server_after_two_failures(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    asked = []

    def query(server):
        asked.append(server)
        return NtpSample(0.128, 0.05) if len(asked) == 4 else None

    assert ntp_offset("time.google.com", query=query) == 0.128
    assert asked == ["time.google.com"] * 2 + ["time.windows.com"] * 3
    assert "Clock checked against time.windows.com: round trip 50 ms (best of 1)" in caplog.text


def test_ntp_offset_keeps_the_answer_with_the_shortest_round_trip(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    # The first check of the test booking on 2026-10-19 took 0.57 s; quick ones agreed.
    answers = iter([(-0.531, 0.570), (-0.413, 0.065), (-0.435, 0.130), (-0.414, 0.041)])
    asked = []

    def query(server):
        asked.append(server)
        return NtpSample(*next(answers))

    assert ntp_offset("time.google.com", query=query) == -0.414
    assert asked == ["time.google.com"] * 4
    assert "Clock checked against time.google.com: round trip 41 ms (best of 4)" in caplog.text


def test_ntp_offset_without_any_answer_is_none(caplog):
    asked = []

    def query(server):
        asked.append(server)

    assert ntp_offset("ntp.example.org", query=query) is None
    assert asked == [
        server
        for server in ("ntp.example.org", "time.google.com", "time.windows.com", "pool.ntp.org")
        for _ in range(2)
    ]
    assert (
        "No time server answered (ntp.example.org, time.google.com, time.windows.com, pool.ntp.org)"
    ) in caplog.text


CHECKED = datetime(2026, 10, 19, 5, 50, 3, 536000)  # the first check on 2026-10-19, PC clock


class WindowsTime:
    """A PC clock that Windows Time sets, and a performance counter that nothing sets.

    Sleeping moves both; ``answers`` are the time server's answers, in turn.
    """

    def __init__(self, *answers):
        self.pc = CHECKED
        self.counter = 1000.0
        self.answers = list(answers)
        self.asked = 0

    def local_now(self):
        return self.pc

    def perf_counter(self):
        return self.counter

    def sleep(self, seconds):
        self.pc += timedelta(seconds=seconds)
        self.counter += seconds

    def set_pc(self, seconds):
        """Set the PC clock by ``seconds``, as Windows does after a synchronisation."""
        self.pc += timedelta(seconds=seconds)

    def measure(self, server):
        self.asked += 1
        return self.answers.pop(0)

    def clock(self, server="time.google.com"):
        return NtpClock(server, self.measure, self.local_now, self.perf_counter)


@pytest.mark.parametrize("change", [0.757, -1.0, 1.0])
def test_the_anchored_time_ignores_the_pc_clock_being_set(change):
    windows = WindowsTime(0.757)
    clock = windows.clock()
    clock.measure()

    windows.set_pc(change)
    windows.sleep(536.464)

    assert clock.now() == CHECKED + timedelta(seconds=0.757 + 536.464)
    assert clock.offset == 0.757


def test_the_first_tap_waits_for_the_ntp_time_after_windows_set_the_pc_clock(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    windows = WindowsTime(0.757)  # the PC clock is 0.757 s slow
    clock = windows.clock()
    clock.measure()
    windows.set_pc(0.757)  # 05:50:21 on 2026-10-19: the PC clock is right from now on
    start = datetime(2026, 10, 19, 6, 0, 0, 100000)

    wait_until(start, now=clock.now, sleep=windows.sleep)

    # The PC clock is right, so it reads the start too; the old wait ended at 05:59:59.343.
    assert abs((windows.pc - start).total_seconds()) < 0.002
    assert "Waiting 595.8 s until 06:00:00.100" in caplog.text


def test_a_later_answer_anchors_the_clock_again_and_logs_the_change(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    windows = WindowsTime(0.757, 0.012)
    clock = windows.clock()
    clock.measure()
    windows.set_pc(0.745)  # Windows slewed most of the error away
    windows.sleep(535.707)  # to 05:58:59.988 by the PC clock, 05:59:00.000 by NTP
    windows.counter += 0.002  # the counter ran 2 ms fast

    clock.measure()

    assert clock.offset == 0.012
    assert clock.now() == datetime(2026, 10, 19, 5, 59, 0)
    assert (
        "Clock offset +0.012 s (-0.745 s since 05:50:03.536; anchored time off by +0.002 s)"
    ) in caplog.text


def test_a_failed_later_check_keeps_the_anchor(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    windows = WindowsTime(0.757, None)
    clock = windows.clock()
    clock.measure()
    windows.set_pc(1.0)

    clock.measure()

    assert clock.offset == 0.757
    assert clock.now() == CHECKED + timedelta(seconds=0.757)
    assert "Keeping the clock offset +0.757 s from 05:50:03.536" in caplog.text


def test_without_an_answer_the_clock_is_the_pc_clock(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    windows = WindowsTime(None)
    clock = windows.clock()

    clock.measure()
    windows.set_pc(1.0)

    assert clock.offset is None
    assert clock.now() == windows.pc
    assert "Using the PC clock" in caplog.text


def test_without_a_server_the_clock_never_asks():
    windows = WindowsTime()
    clock = windows.clock(server="")

    clock.measure()

    assert windows.asked == 0
    assert clock.now() == windows.pc


def test_reading_shows_the_anchored_time_and_the_pc_clock():
    windows = WindowsTime(0.757)
    clock = windows.clock()
    assert clock.reading() == "05:50:03.536 (PC clock)"

    clock.measure()
    windows.set_pc(0.1)

    assert clock.reading() == "05:50:04.293 (NTP), PC clock 05:50:03.636"
