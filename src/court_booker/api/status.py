"""The Overview: what runs now, the schedule, the last run and the last setup."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from collections.abc import Sequence
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from court_booker import __version__, history_read
from court_booker.api.context import AppContext, Context
from court_booker.api.history import RunSummary
from court_booker.api.schedule import ScheduleState, schedule_state
from court_booker.lock import RunLock

router = APIRouter(prefix="/api", tags=["status"])


RECENT_RUNS = 20
"""How many of the newest runs are looked through for those of the run going on now."""


class Running(BaseModel):
    """The run that holds the emulator now; ``since`` is empty while a dry run starts."""

    trigger: str
    pid: int
    since: Optional[str]
    runs: list[int] = []
    """Its history runs: its own, then those of the other MuMu instances it started, in
    instance order. Its own run may have finished already, as the lock goes a moment after
    its last step; empty until its run has started."""


def running(
    context: AppContext, dry_run: Any = None, recent: Sequence[dict[str, Any]] = ()
) -> Optional[Running]:
    """Return the run going on now, from the lock or from the dry run started last.

    ``dry_run`` is the process the backend started last; for its first moments it does not
    hold the lock yet. ``recent`` holds the newest runs, newest first, where its runs are.
    """
    holder = RunLock(context.data.lock).running_holder()
    if holder is not None:
        return Running(
            trigger=holder.trigger,
            pid=holder.pid,
            since=holder.since,
            runs=runs_of(holder.since, recent, context.config().mumu_index),
        )
    if dry_run is not None and dry_run.poll() is None:
        return Running(trigger="dry_run", pid=dry_run.pid, since=None)
    return None


def runs_of(since: str, recent: Sequence[dict[str, Any]], own: int) -> list[int]:
    """Return the runs of the lock holder since ``since``: its own, then its instances'.

    Its own run is the newest run of MuMu instance ``own`` (or of no recorded instance,
    before 0.13.0) that started once the lock was taken; the runs of the other instances
    start after it, from the processes it starts.
    """
    mine = [run for run in recent if run["device"] in (None, own)]
    if not mine or mine[0]["started_at"] < since:
        return []
    first = mine[0]
    others = [
        run
        for run in recent
        if run["device"] not in (None, own) and run["started_at"] >= first["started_at"]
    ]
    return [first["id"], *(run["id"] for run in sorted(others, key=lambda run: run["device"]))]


class SetupSummary(BaseModel):
    """When auto setup last ran, and the items it left for the user."""

    checked_at: str
    left: list[str]


class Overview(BaseModel):
    """Everything the Overview shows, in one call."""

    version: str
    running: Optional[Running]
    schedule: ScheduleState
    last_run: Optional[RunSummary]
    setup: Optional[SetupSummary]
    """Empty until auto setup has run once."""


@router.get("/status", response_model=Overview)
def read_status(context: Context, request: Request) -> Overview:
    """Show what runs now, the schedule and next booking, the last run and the last setup."""
    connection = history_read.open_read_only(context.data.database)
    try:
        recent = history_read.list_runs(connection, limit=RECENT_RUNS)
        setup = history_read.last_setup(connection)
    finally:
        connection.close()
    last = recent[:1]
    return Overview(
        version=__version__,
        running=running(context, getattr(request.app.state, "dry_run", None), recent),
        schedule=schedule_state(context),
        last_run=RunSummary(**last[0]) if last else None,
        setup=SetupSummary(**setup) if setup else None,
    )
