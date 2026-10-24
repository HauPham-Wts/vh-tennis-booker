"""Read the history back for the app: runs, their slots, steps and log lines.

Runs write the database (:mod:`court_booker.history`); the app only reads it, through a
read-only connection, so a page can never change a run's record.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from court_booker.history import SCHEMA_VERSION, connect

DEFAULT_LIMIT = 50

_RUN_COLUMNS = """
    runs.id, runs.trigger, runs.dry_run, runs.version, runs.started_at, runs.finished_at,
    runs.play_date, runs.court, runs.status, runs.error, runs.device,
    (SELECT COUNT(*) FROM run_slots WHERE run_slots.run_id = runs.id AND run_slots.ok) AS booked,
    (SELECT COUNT(*) FROM run_slots WHERE run_slots.run_id = runs.id) AS total
"""

_RUN_DAY = "substr(runs.started_at, 1, 10)"
"""The day a run started; ``started_at`` is local time, ``YYYY-MM-DDTHH:MM:SS.mmm``."""


def open_read_only(path: Path) -> sqlite3.Connection:
    """Open the history at ``path`` for reading; rows come back as ``sqlite3.Row``.

    A missing database is created first (empty, migrated), so a new install reads no runs
    instead of failing, and an older one is migrated first, so the queries find every
    column. The connection may be used from another thread than the one that opened it (the
    backend's worker threads); it only reads.
    """
    if not path.exists():
        connect(path).close()
    connection = _read_only(path)
    if connection.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
        connection.close()
        connect(path).close()
        connection = _read_only(path)
    connection.row_factory = sqlite3.Row
    return connection


def _read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)


def list_runs(
    db: sqlite3.Connection,
    *,
    month: str | None = None,
    trigger: str | None = None,
    dry_run: bool | None = None,
    before: int | None = None,
    days: int | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Return runs newest first, each with its slots and its count of booked and all slots.

    ``month`` (``YYYY-MM``) keeps runs whose play date falls in it; ``dry_run`` keeps dry
    runs or real ones (a scheduled run can be a dry run too); ``before`` (a run id) returns
    the page after the one that ended with that run. ``days`` keeps every run of the newest
    ``days`` days the other filters leave runs on, by the day a run started.
    """
    where, params = [], []
    if month:
        where.append("runs.play_date LIKE ?")
        params.append(f"{month}-%")
    if trigger:
        where.append("runs.trigger = ?")
        params.append(trigger)
    if dry_run is not None:
        where.append("runs.dry_run = ?")
        params.append(int(dry_run))
    if before is not None:
        where.append("runs.id < ?")
        params.append(before)
    if days is not None:
        # The days are counted among the runs the other filters keep, so none comes up empty.
        kept = f" WHERE {' AND '.join(where)}" if where else ""
        where.append(
            f"{_RUN_DAY} IN (SELECT DISTINCT {_RUN_DAY} FROM runs{kept} ORDER BY 1 DESC LIMIT ?)"
        )
        params.extend([*params, days])
    condition = f" WHERE {' AND '.join(where)}" if where else ""
    rows = db.execute(
        f"SELECT {_RUN_COLUMNS} FROM runs{condition} ORDER BY runs.id DESC LIMIT ?",
        [*params, limit],
    )
    runs = [_run(row) for row in rows]
    _add_slots(db, runs)
    return runs


def get_run(db: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    """Return one run with its slots, its steps and its log lines; ``None`` if unknown."""
    row = db.execute(f"SELECT {_RUN_COLUMNS} FROM runs WHERE runs.id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    run = _run(row)
    _add_slots(db, [run])
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


def list_months(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return each month with real bookings, newest first: its runs and its booked slots.

    Months follow the play date; dry runs and runs that never reached a date are left out.
    """
    rows = db.execute(
        "SELECT substr(runs.play_date, 1, 7) AS month, COUNT(DISTINCT runs.id) AS runs,"
        " COALESCE(SUM(run_slots.ok), 0) AS booked"
        " FROM runs LEFT JOIN run_slots ON run_slots.run_id = runs.id"
        " WHERE runs.play_date IS NOT NULL AND NOT runs.dry_run"
        " GROUP BY month ORDER BY month DESC"
    )
    return [dict(row) for row in rows]


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


def events_after(db: sqlite3.Connection, after: int, limit: int = 500) -> list[dict[str, Any]]:
    """Return the activity log steps written after step ``after``, oldest first."""
    rows = db.execute(
        "SELECT id, run_id, time, category, kind, data FROM events WHERE id > ?"
        " ORDER BY id LIMIT ?",
        (after, limit),
    )
    return [_event(row) for row in rows]


def last_event_id(db: sqlite3.Connection) -> int:
    """Return the id of the newest step, or 0 without any."""
    return db.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()[0]


def last_setup(db: sqlite3.Connection) -> dict[str, Any] | None:
    """Return when auto setup last ran and the items it left, or ``None`` if it never ran."""
    row = db.execute(
        "SELECT time, data FROM events WHERE kind = 'setup_finished' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {"checked_at": row["time"], "left": json.loads(row["data"])["left"]}


def dry_run_passed(db: sqlite3.Connection) -> bool:
    """Return whether any dry run went through every slot; scheduling requires one."""
    row = db.execute("SELECT 1 FROM runs WHERE trigger = 'dry_run' AND status = 'ok' LIMIT 1")
    return row.fetchone() is not None


def _add_slots(db: sqlite3.Connection, runs: list[dict[str, Any]]) -> None:
    """Give each run its slots in the order they were tried, with one query for all."""
    by_id = {run["id"]: run for run in runs}
    for run in runs:
        run["slots"] = []
    if not by_id:
        return
    marks = ", ".join("?" * len(by_id))
    for row in db.execute(
        "SELECT run_id, slot, ok, reason, finished_at, seconds, commands FROM run_slots"
        f" WHERE run_id IN ({marks}) ORDER BY id",
        list(by_id),
    ):
        slot = _slot(row)
        by_id[slot.pop("run_id")]["slots"].append(slot)


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
