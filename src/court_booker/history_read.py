"""Read the history back for the app: runs, their slots, steps and log lines.

Runs write the database (:mod:`court_booker.history`); the app only reads it, through a
read-only connection, so a page can never change a run's record.
"""

from __future__ import annotations

import json
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


def get_run(db: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    """Return one run with its slots, its steps and its log lines; ``None`` if unknown."""
    row = db.execute(f"SELECT {_RUN_COLUMNS} FROM runs WHERE runs.id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    run = _run(row)
    run["slots"] = [
        _slot(slot)
        for slot in db.execute(
            "SELECT slot, ok, reason, finished_at, seconds, commands FROM run_slots"
            " WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
    ]
    run["steps"] = [
        _event(event)
        for event in db.execute(
            "SELECT id, run_id, time, category, kind, data FROM events"
            " WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
    ]
    run["log_lines"] = [
        dict(line)
        for line in db.execute(
            "SELECT id, time, level, message FROM log_lines WHERE run_id = ? ORDER BY id",
            (run_id,),
        )
    ]
    return run


def list_events(
    db: sqlite3.Connection,
    *,
    category: str | None = None,
    before: int | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Return activity log steps newest first, of runs and of the app (``run_id`` empty).

    ``category`` keeps one filter (``step``, ``slot``, ``setup``, ``error``...); ``before``
    (a step id) returns the page after the one that ended with that step.
    """
    where, params = [], []
    if category:
        where.append("category = ?")
        params.append(category)
    if before is not None:
        where.append("id < ?")
        params.append(before)
    condition = f" WHERE {' AND '.join(where)}" if where else ""
    rows = db.execute(
        f"SELECT id, run_id, time, category, kind, data FROM events{condition}"
        " ORDER BY id DESC LIMIT ?",
        [*params, limit],
    )
    return [_event(row) for row in rows]


def _run(row: sqlite3.Row) -> dict[str, Any]:
    run = dict(row)
    run["dry_run"] = bool(run["dry_run"])
    return run


def _slot(row: sqlite3.Row) -> dict[str, Any]:
    slot = dict(row)
    slot["ok"] = bool(slot["ok"])
    return slot


def _event(row: sqlite3.Row) -> dict[str, Any]:
    event = dict(row)
    event["data"] = json.loads(event["data"])
    return event
