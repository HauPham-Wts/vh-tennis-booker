"""The history database: every run, its slots, its steps and its log lines.

One SQLite file in the data folder holds the booking history and the activity log. Every run
writes to it, whoever started it (the scheduled task, a dry run, the command line); the app
only reads it. Times are local ISO strings, the same clock as the log files.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

BUSY_TIMEOUT = 0.5
"""Seconds to wait for another writer; longer would delay a booking round."""

MIGRATIONS = (
    """
    CREATE TABLE runs (
        id INTEGER PRIMARY KEY,
        trigger TEXT NOT NULL,
        dry_run INTEGER NOT NULL,
        version TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        play_date TEXT,
        court TEXT,
        status TEXT NOT NULL,
        error TEXT
    );
    CREATE TABLE run_slots (
        id INTEGER PRIMARY KEY,
        run_id INTEGER NOT NULL REFERENCES runs (id),
        slot TEXT NOT NULL,
        ok INTEGER NOT NULL,
        reason TEXT,
        finished_at TEXT NOT NULL,
        seconds REAL NOT NULL,
        commands INTEGER NOT NULL
    );
    CREATE TABLE events (
        id INTEGER PRIMARY KEY,
        run_id INTEGER REFERENCES runs (id),
        time TEXT NOT NULL,
        category TEXT NOT NULL,
        kind TEXT NOT NULL,
        data TEXT NOT NULL
    );
    CREATE TABLE log_lines (
        id INTEGER PRIMARY KEY,
        run_id INTEGER REFERENCES runs (id),
        time TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL
    );
    CREATE INDEX run_slots_by_run ON run_slots (run_id);
    CREATE INDEX events_by_run ON events (run_id);
    CREATE INDEX log_lines_by_run ON log_lines (run_id);
    """,
)
"""Schema changes in order; ``PRAGMA user_version`` counts the ones applied."""

SCHEMA_VERSION = len(MIGRATIONS)


def migrate(connection: sqlite3.Connection) -> int:
    """Apply the missing schema changes and return the schema version.

    A database written by a newer version is left as it is: its changes only add tables
    and columns, so older code can still write to it.
    """
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        connection.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;")
        logger.debug("History database schema %d applied", number)
    return max(version, SCHEMA_VERSION)


def connect(path: Path) -> sqlite3.Connection:
    """Open the database at ``path``, creating and migrating it as needed.

    Write-ahead logging lets the app read while a run writes, and without a disk flush on
    every commit a write takes well under a millisecond.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=BUSY_TIMEOUT)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA foreign_keys = ON")
        migrate(connection)
    except sqlite3.Error:
        connection.close()
        raise
    return connection
