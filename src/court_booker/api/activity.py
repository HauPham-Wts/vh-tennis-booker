"""Record what the app itself does (settings saved, schedule switched) in the activity log."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from court_booker.api.context import AppContext
from court_booker.events import EventKind, Reporter
from court_booker.history import History, connect

logger = logging.getLogger(__name__)


def record(context: AppContext, kind: EventKind, **data: Any) -> None:
    """Write one app event, without a run, to the history.

    A database that cannot be written is logged: the change the event reports is done
    already and stays done.
    """
    try:
        store = History(connect(context.data.database))
    except (OSError, sqlite3.Error):
        logger.warning("Could not record %s in the history", kind.value, exc_info=True)
        return
    try:
        Reporter(store)(kind, **data)
    finally:
        store.close()
