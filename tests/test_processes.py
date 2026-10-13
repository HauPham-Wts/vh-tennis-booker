"""Tests for telling running processes apart, with real processes."""

import subprocess
import sys
import time

import pytest

from court_booker import processes


def finished_process_id():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    return child.pid


def test_this_process_is_running():
    pid, started = processes.current()

    assert processes.is_running(pid, started)


def test_a_finished_process_is_not_running():
    pid = finished_process_id()

    assert processes.start_time(pid) is None
    assert not processes.is_running(pid, 0.0)


@pytest.mark.skipif(sys.platform != "win32", reason="start times are read on Windows only")
def test_another_start_time_means_another_process():
    pid, started = processes.current()

    assert not processes.is_running(pid, started - 60)
    assert started < time.time() < started + 24 * 3600


def test_an_uninspectable_process_counts_as_running(monkeypatch):
    def denied(pid):
        raise PermissionError(pid)

    monkeypatch.setattr(processes, "start_time", denied)

    assert processes.is_running(4, 0.0)


def test_stop_ends_a_process():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    pid, started = child.pid, processes.start_time(child.pid)
    assert started is not None

    processes.stop(pid)
    child.wait(timeout=10)

    assert not processes.is_running(pid, started)
