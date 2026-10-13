"""Read the history back for the app: runs, their slots, steps and log lines.

Runs write the database (:mod:`court_booker.history`); the app only reads it, through a
read-only connection, so a page can never change a run's record.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from court_booker.history import connect


def open_read_only(path: Path) -> sqlite3.Connection:
    """Open the history at ``path`` for reading; rows come back as ``sqlite3.Row``.

    A missing database is created first (empty, migrated), so a new install reads no runs
    instead of failing.
    """
    if not path.exists():
        connect(path).close()
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection
