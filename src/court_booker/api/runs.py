"""Run routes: start a dry run from the app."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from court_booker.api.context import Context
from court_booker.errors import LockHeldError
from court_booker.lock import RunLock, check_quiet_time

router = APIRouter(prefix="/api", tags=["runs"])

# Keep a console window from opening for the dry run.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_starting = threading.Lock()
"""Two requests at once must not both find no run and both start one."""


def launch(config_path: Path) -> "subprocess.Popen[bytes]":
    """Start ``court-booker --dry-run`` in its own process, as the scheduled task starts a run.

    The dry run then takes the exact code path of the 06:00 run, writes its own history and
    log file, and a crash in it cannot take the backend down. The packaged app (0.7.0)
    will start its own executable instead of ``python -m``.
    """
    return subprocess.Popen(
        [sys.executable, "-m", "court_booker", "--dry-run", "--config", str(config_path)],
        cwd=config_path.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )


class DryRunStarted(BaseModel):
    """A dry run has started; its steps show in the history as it goes."""

    pid: int
    started_at: str


@router.post("/runs/dry-run", status_code=202, response_model=DryRunStarted)
def start_dry_run(context: Context, request: Request) -> DryRunStarted:
    """Start a dry run of the saved settings; it stops before "Xác nhận".

    Refused (400 ``bad_request``) from the wake time to 5 minutes after the start time and
    (409 ``lock_held``) while a run holds the lock, or while the dry run started last is
    still running (it may not hold the lock yet). The dry run checks again itself.
    """
    config = context.config()
    now = datetime.now()
    check_quiet_time(now, config.wake_at, config.start_at, "dry run")
    with _starting:
        last = getattr(request.app.state, "dry_run", None)
        if last is not None and last.poll() is None:
            raise LockHeldError(f"Another run is in progress: dry run (pid {last.pid})")
        holder = RunLock(context.data.lock).running_holder()
        if holder is not None:
            raise LockHeldError(f"Another run is in progress: {holder.describe()}")
        process = launch(context.config_path.resolve())
        request.app.state.dry_run = process
    return DryRunStarted(pid=process.pid, started_at=now.isoformat(timespec="seconds"))
