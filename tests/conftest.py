import logging
import sys
from datetime import datetime, timedelta
from itertools import count
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def record_run():
    """Return a function that writes one run to a history database, as a real run does."""
    from court_booker import history
    from court_booker.events import EventKind, Reporter

    moments = (datetime(2026, 10, 13, 5, 50) + timedelta(seconds=step) for step in count())

    def record(
        path, trigger="scheduled", date="2026-10-15", slots=(), status="ok", dry_run=None, day=None
    ):
        """Write a run with ``slots`` as ``(slot, booked)`` pairs; return its id.

        A run is a dry run when its trigger says so, unless ``dry_run`` is given (a
        scheduled task can be tested with --dry-run). ``day`` (``YYYY-MM-DD``) moves the
        run from 2026-10-13 to that day.
        """
        shift = timedelta() if day is None else datetime.fromisoformat(day) - datetime(2026, 10, 13)
        store = history.History(history.connect(path))
        report = Reporter(store, clock=lambda: next(moments) + shift)
        dry = trigger == "dry_run" if dry_run is None else dry_run
        report(EventKind.RUN_STARTED, trigger=trigger, dry_run=dry, version="0.5.0")
        if date:
            report(EventKind.BOOKING_STARTED, date=date, court="S6 - Sân tennis", slots=[])
        for slot, booked in slots:
            report(EventKind.SLOT_STARTED, slot=slot, round=1, rounds=len(slots))
            if booked:
                report(EventKind.SLOT_BOOKED, slot=slot, seconds=7.8, commands=51, dry_run=False)
            else:
                report(
                    EventKind.SLOT_FAILED,
                    slot=slot,
                    reason="fully booked",
                    seconds=2.1,
                    commands=12,
                )
        report(EventKind.RUN_FINISHED, status=status, booked=0, total=0, error=None)
        store.close()
        return store.run_id

    return record


@pytest.fixture(autouse=True)
def data_home(tmp_path, monkeypatch):
    """Point the data folder at a temporary one, so tests never touch the real history."""
    home = tmp_path / "home"
    monkeypatch.setenv("COURT_BOOKER_HOME", str(home))
    return home


@pytest.fixture(autouse=True)
def restore_package_logger():
    """Undo ``configure_logging`` after each test.

    It turns off propagation on the package logger, which hides records from
    ``caplog`` in later tests (pytest 8 and older).
    """
    logger = logging.getLogger("court_booker")
    saved = (logger.handlers[:], logger.level, logger.propagate)
    yield
    for handler in logger.handlers:
        if handler not in saved[0]:
            handler.close()
    logger.handlers[:], logger.level, logger.propagate = saved
