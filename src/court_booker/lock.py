"""The run lock: one task drives the emulator at a time.

Runs take it (the scheduled run, dry runs, command-line runs); viewing pages and saving
settings do not. The lock is a JSON file in the data folder that names its holder: the
process id and start time, what started the run and when it took the lock.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from court_booker import processes
from court_booker.errors import LockHeldError
from court_booker.events import EventKind, Reporter

logger = logging.getLogger(__name__)

_ATTEMPTS = 3
"""Tries to take the lock when others clear or release it at the same moment."""


class ProcessTable(Protocol):
    """The processes of the machine, as :mod:`court_booker.processes` sees them."""

    def current(self) -> tuple[int, float]: ...

    def is_running(self, pid: int, started: float) -> bool: ...

    def stop(self, pid: int) -> None: ...


@dataclass(frozen=True)
class Holder:
    """The run named in the lock file."""

    pid: int
    process_started: float
    trigger: str
    since: str

    def describe(self) -> str:
        return f"{self.trigger} run (pid {self.pid}) since {self.since[11:19]}"

    def fields(self) -> dict[str, Any]:
        """Return the details reported in events."""
        return {"trigger": self.trigger, "pid": self.pid, "since": self.since}


UNREADABLE = Holder(pid=-1, process_started=0.0, trigger="unknown", since="")
"""Stands for a lock file whose content cannot be read."""


class RunLock:
    """The lock file at ``path``, taken and released by this process.

    A lock whose holder is no longer running (the PC lost power, the process was killed) is
    removed when the next run takes the lock.
    """

    def __init__(
        self,
        path: Path,
        report: Reporter | None = None,
        table: ProcessTable = processes,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.path = path
        self.report = Reporter() if report is None else report
        self.table = table
        self._clock = clock
        self.held: Holder | None = None

    def holder(self) -> Holder | None:
        """Return the holder named in the lock file, or ``None`` if there is no lock."""
        try:
            return Holder(**json.loads(self.path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError):
            return UNREADABLE

    def acquire(self, trigger: str) -> None:
        """Take the lock for a run started by ``trigger``.

        Raises ``LockHeldError`` if another run holds it.
        """
        holder = self._take(trigger)
        if holder is not None:
            raise LockHeldError(f"Another run is in progress: {self._describe(holder)}")

    def release(self) -> None:
        """Give the lock back, unless another run has taken it over meanwhile."""
        if self.held is not None:
            self._remove_if(self.held)
            logger.debug("Run lock released")
            self.held = None

    def _take(self, trigger: str) -> Holder | None:
        """Take the lock, clearing one whose holder is gone; return a running holder."""
        for _ in range(_ATTEMPTS):
            if self._create(trigger):
                return None
            holder = self.holder()
            if holder is None:  # released meanwhile
                continue
            if holder is not UNREADABLE and self.table.is_running(
                holder.pid, holder.process_started
            ):
                return holder
            logger.warning(
                "Removed the run lock of %s: it is no longer running", self._describe(holder)
            )
            self.report(EventKind.LOCK_CLEARED, **holder.fields())
            self._remove_if(holder)
        return self.holder() or UNREADABLE

    def _create(self, trigger: str) -> bool:
        """Write the lock for this process; ``False`` if a lock file exists."""
        pid, started = self.table.current()
        holder = Holder(pid, started, trigger, self._clock().isoformat(timespec="seconds"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Written aside, then linked in one step: the link fails if a lock exists, and
        # nobody ever reads a half-written lock.
        temp = self.path.with_name(f"{self.path.name}.{pid}.tmp")
        temp.write_text(json.dumps(asdict(holder)), encoding="utf-8")
        try:
            os.link(temp, self.path)
        except FileExistsError:
            return False
        finally:
            temp.unlink()
        self.held = holder
        logger.debug("Run lock taken: %s", holder.describe())
        return True

    def _remove_if(self, holder: Holder | None) -> None:
        """Delete the lock file if it still names ``holder``."""
        if holder is not None and self.holder() == holder:
            self.path.unlink(missing_ok=True)

    @staticmethod
    def _describe(holder: Holder | None) -> str:
        if holder is None or holder is UNREADABLE:
            return "unknown run"
        return holder.describe()
