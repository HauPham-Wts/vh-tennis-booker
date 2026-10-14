"""The Overview: what runs now, the schedule, the last run and the last setup."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from court_booker import __version__, history_read
from court_booker.api.context import AppContext, Context
from court_booker.api.history import RunSummary
from court_booker.api.schedule import ScheduleState, schedule_state
from court_booker.lock import RunLock

router = APIRouter(prefix="/api", tags=["status"])


class Running(BaseModel):
    """The run that holds the emulator now; ``since`` is empty while a dry run starts."""

    trigger: str
    pid: int
    since: Optional[str]


def running(context: AppContext, dry_run: Any = None) -> Optional[Running]:
    """Return the run going on now, from the lock or from the dry run started last.

    ``dry_run`` is the process the backend started last; for its first moments it does not
    hold the lock yet.
    """
    holder = RunLock(context.data.lock).running_holder()
    if holder is not None:
        return Running(trigger=holder.trigger, pid=holder.pid, since=holder.since)
    if dry_run is not None and dry_run.poll() is None:
        return Running(trigger="dry_run", pid=dry_run.pid, since=None)
    return None


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
        last = history_read.list_runs(connection, limit=1)
        setup = history_read.last_setup(connection)
    finally:
        connection.close()
    return Overview(
        version=__version__,
        running=running(context, getattr(request.app.state, "dry_run", None)),
        schedule=schedule_state(context),
        last_run=RunSummary(**last[0]) if last else None,
        setup=SetupSummary(**setup) if setup else None,
    )
