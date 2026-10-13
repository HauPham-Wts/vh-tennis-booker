"""Tests for the run lock, with a fake process table."""

import json
from datetime import datetime, timedelta

import pytest

from court_booker.errors import LockHeldError, RequestError
from court_booker.events import EventKind, MemorySink, Reporter
from court_booker.lock import UNREADABLE, Holder, RunLock, check_quiet_time, schedule_window

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


class FakeTime:
    """A clock that moves only when the code sleeps; ``on_sleep`` runs after each sleep."""

    def __init__(self, now, on_sleep=lambda now: None):
        self.now = now
        self.on_sleep = on_sleep

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.on_sleep(self.now)


WAKE = datetime(2026, 10, 14, 5, 50)
TAKE_OVER = datetime(2026, 10, 14, 5, 58)


def scheduled_lock(path, machine, clock, sink):
    return RunLock(path, Reporter(sink), FakeProcesses(machine, 300), clock=clock)


def test_the_scheduled_run_takes_a_free_lock_at_once(tmp_path, machine):
    sink = MemorySink()
    clock = FakeTime(WAKE)
    lock = scheduled_lock(tmp_path / "run.lock", machine, clock, sink)

    lock.acquire_for_schedule("scheduled", TAKE_OVER, sleep=clock.sleep)

    assert lock.holder().pid == 300
    assert clock.now == WAKE
    assert sink.kinds == []


def test_the_scheduled_run_waits_for_a_run_to_finish(tmp_path, machine):
    path = tmp_path / "run.lock"
    dry_run = lock_for(path, machine, 100)
    dry_run.acquire("dry_run")
    finish = WAKE + timedelta(seconds=30)
    clock = FakeTime(WAKE, on_sleep=lambda now: now >= finish and dry_run.release())
    sink = MemorySink()
    lock = scheduled_lock(path, machine, clock, sink)

    lock.acquire_for_schedule("scheduled", TAKE_OVER, sleep=clock.sleep)

    assert lock.holder().pid == 300
    assert clock.now == finish
    assert sink.kinds == [EventKind.LOCK_WAITING]
    assert machine.stopped == []


def test_the_scheduled_run_stops_a_run_that_holds_on(tmp_path, machine, caplog):
    path = tmp_path / "run.lock"
    lock_for(path, machine, 100).acquire("dry_run")
    clock = FakeTime(TAKE_OVER - timedelta(seconds=10))
    sink = MemorySink()
    lock = scheduled_lock(path, machine, clock, sink)

    lock.acquire_for_schedule("scheduled", TAKE_OVER, sleep=clock.sleep)

    assert machine.stopped == [100]
    assert clock.now == TAKE_OVER
    assert lock.holder().pid == 300
    assert sink.kinds == [EventKind.LOCK_WAITING, EventKind.LOCK_TAKEN_OVER]
    assert "Stopping dry_run run (pid 100) since 10:43:10 to keep the scheduled run" in caplog.text


def test_a_late_scheduled_run_stops_the_other_run_at_once(tmp_path, machine):
    path = tmp_path / "run.lock"
    lock_for(path, machine, 100).acquire("manual")
    clock = FakeTime(TAKE_OVER + timedelta(minutes=1))
    lock = scheduled_lock(path, machine, clock, MemorySink())

    lock.acquire_for_schedule("scheduled", TAKE_OVER, sleep=clock.sleep)

    assert machine.stopped == [100]
    assert clock.now == TAKE_OVER + timedelta(minutes=1)


def test_the_scheduled_run_takes_the_lock_of_a_run_it_cannot_stop(tmp_path, machine, caplog):
    path = tmp_path / "run.lock"
    lock_for(path, machine, 100).acquire("dry_run")

    def refuse(pid):
        raise PermissionError(pid)

    table = FakeProcesses(machine, 300)
    table.stop = refuse
    clock = FakeTime(TAKE_OVER)
    lock = RunLock(path, table=table, clock=clock)

    lock.acquire_for_schedule("scheduled", TAKE_OVER, sleep=clock.sleep)

    assert lock.holder().pid == 300
    assert "Could not stop process 100" in caplog.text
    assert "still running; taking its lock anyway" in caplog.text


def test_a_lock_that_cannot_be_written_does_not_stop_the_run(tmp_path, machine, caplog):
    (tmp_path / "home").write_text("not a folder", encoding="utf-8")
    path = tmp_path / "home" / "run.lock"
    lock = lock_for(path, machine, 100)
    clock = FakeTime(WAKE)
    scheduled = scheduled_lock(path, machine, clock, MemorySink())

    lock.acquire("dry_run")
    scheduled.acquire_for_schedule("scheduled", TAKE_OVER, sleep=clock.sleep)
    lock.release()

    assert lock.held is None
    assert caplog.text.count("unavailable; running without it") == 2


def test_the_schedule_window_runs_from_wake_to_five_minutes_after_the_start():
    begin, end = schedule_window(WAKE.date(), "05:50", "06:00")

    assert begin == WAKE
    assert end == datetime(2026, 10, 14, 6, 5)


def test_quiet_time_refuses_a_task_inside_the_window():
    check_quiet_time(datetime(2026, 10, 14, 6, 5), "05:50", "06:00", "dry run")

    with pytest.raises(RequestError, match="No dry run from 05:50 to 06:05"):
        check_quiet_time(datetime(2026, 10, 14, 5, 50), "05:50", "06:00", "dry run")


def test_an_unreadable_lock_is_cleared(tmp_path, machine):
    path = tmp_path / "run.lock"
    path.write_text("{", encoding="utf-8")
    lock = lock_for(path, machine, 200)

    lock.acquire("dry_run")

    assert lock.holder().pid == 200
