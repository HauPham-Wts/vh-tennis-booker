"""Schedule routes: the daily Task Scheduler task that books at the start time."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from court_booker import history_read, schedule
from court_booker.api.context import AppContext, Context

router = APIRouter(prefix="/api", tags=["schedule"])


class ScheduleState(BaseModel):
    """The schedule and the next booking it makes."""

    enabled: bool
    wake_at: str
    start_at: str
    next_start: str
    """When the next booking starts, ``YYYY-MM-DDTHH:MM``."""
    next_play_date: str
    """The day that booking is for."""
    dry_run_passed: bool
    """The schedule may be switched on only once a dry run has passed."""


def schedule_state(context: AppContext) -> ScheduleState:
    """Return the schedule as the app shows it."""
    config = context.config()
    start = schedule.next_start(datetime.now(), config.start_at)
    connection = history_read.open_read_only(context.data.database)
    try:
        passed = history_read.dry_run_passed(connection)
    finally:
        connection.close()
    return ScheduleState(
        enabled=schedule.installed(),
        wake_at=config.wake_at,
        start_at=config.start_at,
        next_start=start.isoformat(timespec="minutes"),
        next_play_date=(start.date() + timedelta(days=config.days_ahead)).isoformat(),
        dry_run_passed=passed,
    )


@router.get("/schedule", response_model=ScheduleState)
def read_schedule(context: Context) -> ScheduleState:
    """Show whether the daily booking is on, and the next one."""
    return schedule_state(context)
