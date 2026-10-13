"""The Overview: what runs now, the schedule, the last run and the last setup."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from typing import Any, Optional

from pydantic import BaseModel

from court_booker.api.context import AppContext
from court_booker.lock import RunLock


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
