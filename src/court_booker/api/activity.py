"""Record what the app itself does (settings saved, auto setup) in the activity log."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from court_booker.api.context import AppContext
from court_booker.events import EventKind, LogSink, MultiSink, Reporter
from court_booker.history import History, connect

logger = logging.getLogger(__name__)


def open_store(context: AppContext) -> History | None:
    """Open the history to write app events; ``None`` (logged) if it cannot be opened.

    Unlike a run, the backend does not copy its log lines into the history: they would
    mix the lines of every request.
    """
    try:
        return History(connect(context.data.database))
    except (OSError, sqlite3.Error):
        logger.warning("History database unavailable; app events not recorded", exc_info=True)
        return None


def reporter(store: History | None) -> Reporter:
    """Report events to the debug log and, when open, to ``store``."""
    return Reporter(LogSink() if store is None else MultiSink(LogSink(), store))


def record(context: AppContext, kind: EventKind, **data: Any) -> None:
    """Write one app event, without a run, to the history.

    A database that cannot be written is logged: the change the event reports is done
    already and stays done.
    """
    store = open_store(context)
    if store is None:
        return
    try:
        Reporter(store)(kind, **data)
    finally:
        store.close()
