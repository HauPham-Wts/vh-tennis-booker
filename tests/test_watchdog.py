"""Tests for the time limit on device commands; a hung call is waited for 0.05 s."""

import threading

import pytest

from court_booker.errors import DeviceNotRespondingError
from court_booker.watchdog import GuardedDevice, Watchdog


@pytest.fixture
def frozen():
    """Return an event that a hung call waits on; set afterwards so its thread ends."""
    event = threading.Event()
    yield event
    event.set()


def test_a_call_returns_its_result_from_the_worker():
    watchdog = Watchdog(timeout=5)

    assert watchdog.run("dump_hierarchy", lambda: threading.current_thread().name) == "device"


def test_an_error_of_the_call_reaches_the_caller():
    def fail():
        raise ValueError("no such element")

    with pytest.raises(ValueError, match="no such element"):
        Watchdog(timeout=5).run("click", fail)


def test_a_hung_call_ends_the_wait_and_every_later_call(frozen):
    watchdog = Watchdog(timeout=0.05)
    later = []

    with pytest.raises(
        DeviceNotRespondingError, match=r"did not answer dump_hierarchy within 0.05 s"
    ):
        watchdog.run("dump_hierarchy", frozen.wait)
    with pytest.raises(DeviceNotRespondingError, match=r"stopped answering earlier \(dump_hier"):
        watchdog.run("click", lambda: later.append("click"))

    assert watchdog.hung == "dump_hierarchy"
    assert later == []


class Device:
    serial = "127.0.0.1:16384"

    def click(self, x, y):
        return threading.current_thread().name, x, y


def test_guarded_device_sends_method_calls_through_the_watchdog():
    device = GuardedDevice(Device(), Watchdog(timeout=5))

    assert device.click(270, y=1537) == ("device", 270, 1537)
    assert device.serial == "127.0.0.1:16384"
