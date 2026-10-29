"""Schedule routes: the daily Task Scheduler task that books at the start time."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from court_booker import device_setup, history_read, schedule
from court_booker.api.activity import record
from court_booker.api.context import AppContext, Context
from court_booker.api.errors import DryRunRequiredError
from court_booker.clock import parse_time
from court_booker.config import DAYS_AHEAD
from court_booker.errors import RequestError
from court_booker.events import EventKind

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
        next_play_date=(start.date() + timedelta(days=DAYS_AHEAD)).isoformat(),
        dry_run_passed=passed,
    )


@router.get("/schedule", response_model=ScheduleState)
def read_schedule(context: Context) -> ScheduleState:
    """Show whether the daily booking is on, and the next one."""
    return schedule_state(context)


class ScheduleSwitch(BaseModel):
    """Switch the daily booking on or off."""

    enabled: bool


@router.put("/schedule", response_model=ScheduleState)
def switch_schedule(context: Context, switch: ScheduleSwitch) -> ScheduleState:
    """Switch the daily booking on or off.

    Switching on needs a passed dry run (409 ``dry_run_required``) and a wake time before
    the start time (400 ``bad_request``). It installs the task again each time, so a new
    wake time applies, and allows wake timers; ``wake_blocked`` in the Overview tells when
    Windows still keeps them off. The task runs the Python of this backend; in development, the
    runner folder keeps its task through ``tools/setup_runner.py`` instead.
    """
    state = schedule_state(context)
    config = context.config()
    if switch.enabled:
        if not state.dry_run_passed:
            raise DryRunRequiredError("Pass a dry run before switching the schedule on")
        if parse_time(config.wake_at, "wake_at") >= parse_time(config.start_at, "start_at"):
            raise RequestError(f"wake_at {config.wake_at} must be before {config.start_at}")
        schedule.install(context.config_path.resolve(), config.wake_at)
        device_setup.ensure_wake_timers()
        record(
            context, EventKind.SCHEDULE_ENABLED, wake_at=config.wake_at, start_at=config.start_at
        )
    elif state.enabled:
        schedule.remove()
        record(context, EventKind.SCHEDULE_DISABLED)
    return schedule_state(context)
