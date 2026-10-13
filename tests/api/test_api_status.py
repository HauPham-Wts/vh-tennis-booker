"""Tests for the Overview status."""

import json

from court_booker import processes
from court_booker.api import status
from court_booker.lock import Holder


class Process:
    pid = 4321

    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


def hold_lock(context, trigger="scheduled"):
    context.data.ensure()
    pid, started = processes.current()
    holder = Holder(pid, started, trigger, "2026-10-14T05:50:01")
    context.data.lock.write_text(json.dumps(vars(holder)), encoding="utf-8")
    return pid


def test_nothing_runs(context):
    assert status.running(context) is None
    assert status.running(context, Process(code=0)) is None


def test_the_lock_holder_runs(context):
    pid = hold_lock(context)

    assert status.running(context, Process()).model_dump() == {
        "trigger": "scheduled",
        "pid": pid,
        "since": "2026-10-14T05:50:01",
    }


def test_a_starting_dry_run_runs(context):
    assert status.running(context, Process()).model_dump() == {
        "trigger": "dry_run",
        "pid": 4321,
        "since": None,
    }
