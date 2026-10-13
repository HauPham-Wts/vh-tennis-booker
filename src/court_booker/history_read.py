"""Read the history back for the app: runs, their slots, steps and log lines.

Runs write the database (:mod:`court_booker.history`); the app only reads it, through a
read-only connection, so a page can never change a run's record.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from court_booker.history import connect

DEFAULT_LIMIT = 50

_RUN_COLUMNS = """
    runs.id, runs.trigger, runs.dry_run, runs.version, runs.started_at, runs.finished_at,
    runs.play_date, runs.court, runs.status, runs.error,
    (SELECT COUNT(*) FROM run_slots WHERE run_slots.run_id = runs.id AND run_slots.ok) AS booked,
    (SELECT COUNT(*) FROM run_slots WHERE run_slots.run_id = runs.id) AS total
"""


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


def list_runs(
    db: sqlite3.Connection,
    *,
    month: str | None = None,
    trigger: str | None = None,
    before: int | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Return runs newest first, each with its count of booked and of all slots.

    ``month`` (``YYYY-MM``) keeps runs whose play date falls in it; ``before`` (a run id)
    returns the page after the one that ended with that run.
    """
    where, params = [], []
    if month:
        where.append("runs.play_date LIKE ?")
        params.append(f"{month}-%")
    if trigger:
        where.append("runs.trigger = ?")
        params.append(trigger)
    if before is not None:
        where.append("runs.id < ?")
        params.append(before)
    condition = f" WHERE {' AND '.join(where)}" if where else ""
    rows = db.execute(
        f"SELECT {_RUN_COLUMNS} FROM runs{condition} ORDER BY runs.id DESC LIMIT ?",
        [*params, limit],
    )
    return [_run(row) for row in rows]


def _run(row: sqlite3.Row) -> dict[str, Any]:
    run = dict(row)
    run["dry_run"] = bool(run["dry_run"])
    return run
