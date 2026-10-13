"""Tests for the run lock, with a fake process table."""

import json
from datetime import datetime

import pytest

from court_booker.errors import LockHeldError
from court_booker.events import EventKind, MemorySink, Reporter
from court_booker.lock import UNREADABLE, Holder, RunLock

NOW = datetime(2026, 10, 13, 10, 43, 10)


class Machine:
    """The processes running on a fake machine."""

    def __init__(self):
        self.running = set()
        self.stopped = []


class FakeProcesses:
    """One process of a :class:`Machine`, seen through the process table."""

    def __init__(self, machine, pid, started=1000.0):
        self.machine = machine
        self.me = (pid, started)
        machine.running.add(self.me)

    def current(self):
        return self.me

    def is_running(self, pid, started):
        return (pid, started) in self.machine.running

    def stop(self, pid):
        self.machine.stopped.append(pid)
        self.machine.running = {entry for entry in self.machine.running if entry[0] != pid}


@pytest.fixture
def machine():
    return Machine()


def lock_for(path, machine, pid, **kwargs):
    return RunLock(path, table=FakeProcesses(machine, pid), clock=lambda: NOW, **kwargs)


def test_acquire_writes_who_holds_the_lock(tmp_path, machine):
    path = tmp_path / "data" / "run.lock"
    lock = lock_for(path, machine, 100)

    lock.acquire("dry_run")

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "pid": 100,
        "process_started": 1000.0,
        "trigger": "dry_run",
        "since": "2026-10-13T10:43:10",
    }
    assert lock.held == lock.holder() == Holder(100, 1000.0, "dry_run", "2026-10-13T10:43:10")
    assert sorted(item.name for item in path.parent.iterdir()) == ["run.lock"]


def test_a_second_run_is_refused(tmp_path, machine):
    path = tmp_path / "run.lock"
    lock_for(path, machine, 100).acquire("dry_run")
    second = lock_for(path, machine, 200)

    with pytest.raises(LockHeldError, match=r"dry_run run \(pid 100\) since 10:43:10"):
        second.acquire("manual")

    assert second.held is None
    assert second.holder().pid == 100


def test_release_lets_the_next_run_in(tmp_path, machine):
    path = tmp_path / "run.lock"
    first = lock_for(path, machine, 100)
    first.acquire("dry_run")

    first.release()
    lock_for(path, machine, 200).acquire("manual")

    assert first.held is None
    assert first.holder().pid == 200


def test_release_keeps_a_lock_taken_over_by_another_run(tmp_path, machine):
    path = tmp_path / "run.lock"
    first = lock_for(path, machine, 100)
    first.acquire("dry_run")
    path.write_text(json.dumps(vars(Holder(200, 5.0, "scheduled", "x"))), encoding="utf-8")

    first.release()

    assert first.holder().pid == 200


def test_without_a_lock_there_is_no_holder(tmp_path, machine):
    assert lock_for(tmp_path / "run.lock", machine, 100).holder() is None


def test_an_unreadable_lock_has_an_unknown_holder(tmp_path, machine):
    path = tmp_path / "run.lock"
    path.write_text("{", encoding="utf-8")

    assert lock_for(path, machine, 100).holder() is UNREADABLE


def test_the_lock_of_a_run_that_is_gone_is_cleared(tmp_path, machine, caplog):
    path = tmp_path / "run.lock"
    lock_for(path, machine, 100).acquire("scheduled")
    machine.running.discard((100, 1000.0))  # the PC lost power during the run
    sink = MemorySink()
    lock = lock_for(path, machine, 200, report=Reporter(sink))

    lock.acquire("dry_run")

    assert lock.holder().pid == 200
    assert "Removed the run lock of scheduled run (pid 100) since 10:43:10" in caplog.text
    assert sink.kinds == [EventKind.LOCK_CLEARED]
    assert sink.events[0].data == {
        "trigger": "scheduled",
        "pid": 100,
        "since": "2026-10-13T10:43:10",
    }


def test_a_reused_process_id_does_not_keep_the_lock(tmp_path, machine):
    path = tmp_path / "run.lock"
    lock_for(path, machine, 100).acquire("scheduled")
    machine.running = {(100, 2000.0)}  # pid 100 now names a later process

    lock_for(path, machine, 200).acquire("dry_run")

    assert machine.stopped == []


def test_an_unreadable_lock_is_cleared(tmp_path, machine):
    path = tmp_path / "run.lock"
    path.write_text("{", encoding="utf-8")
    lock = lock_for(path, machine, 200)

    lock.acquire("dry_run")

    assert lock.holder().pid == 200
