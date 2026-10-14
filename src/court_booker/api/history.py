"""History and activity routes: what the runs did, read-only."""

# No `from __future__ import annotations`: FastAPI and Pydantic read these annotations at
# run time, where Python 3.9 has no `X | None`, so `Optional` is used instead.
import sqlite3
from collections.abc import Iterator
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from court_booker import history_read
from court_booker.api.context import Context
from court_booker.api.errors import NotFoundError
from court_booker.events import EventKind

router = APIRouter(prefix="/api", tags=["history"])

Trigger = Literal["scheduled", "dry_run", "manual"]
Category = Literal["step", "slot", "setup", "schedule", "settings", "error"]


def history_db(context: Context) -> Iterator[sqlite3.Connection]:
    """Open the history read-only for one request."""
    connection = history_read.open_read_only(context.data.database)
    try:
        yield connection
    finally:
        connection.close()


HistoryDb = Annotated[sqlite3.Connection, Depends(history_db)]


class SlotResult(BaseModel):
    """The result of one slot of a run."""

    slot: str
    ok: bool
    reason: Optional[str]
    finished_at: str
    seconds: float
    commands: int


class RunSummary(BaseModel):
    """One run as the History list shows it."""

    id: int
    trigger: str
    dry_run: bool
    version: str
    started_at: str
    finished_at: Optional[str]
    play_date: Optional[str]
    court: Optional[str]
    status: str
    error: Optional[str]
    booked: int
    total: int
    slots: list[SlotResult]
    """The slots tried, in order, with their results."""


class Step(BaseModel):
    """One step of the activity log; ``kind`` is the message key, ``data`` its values.

    ``kind`` and ``category`` are listed in the schema, so the UI's types name every step
    and a step without a message fails its type check.
    """

    id: int
    run_id: Optional[int]
    time: str
    category: Category
    kind: EventKind
    data: dict[str, Any]


class LogLine(BaseModel):
    """One technical log line."""

    id: int
    time: str
    level: str
    message: str


class RunDetail(RunSummary):
    """One run in full, for its History page."""

    steps: list[Step]
    log_lines: list[LogLine]


@router.get("/runs", response_model=list[RunSummary])
def list_runs(
    db: HistoryDb,
    month: Annotated[Optional[str], Query(pattern=r"^\d{4}-\d{2}$")] = None,
    trigger: Optional[Trigger] = None,
    dry_run: Optional[bool] = None,
    before: Optional[int] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = history_read.DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """List runs newest first.

    ``month`` filters on the play date, ``dry_run`` keeps dry runs or real bookings,
    ``before`` pages back.
    """
    return history_read.list_runs(
        db, month=month, trigger=trigger, dry_run=dry_run, before=before, limit=limit
    )


class MonthSummary(BaseModel):
    """One month with real bookings: how many runs, how many slots they booked."""

    month: str
    runs: int
    booked: int


# Declared before /runs/{run_id}, which would otherwise take "months" for a run id.
@router.get("/runs/months", response_model=list[MonthSummary])
def list_months(db: HistoryDb) -> list[dict[str, Any]]:
    """List the months of real bookings by play date, newest first, with their totals."""
    return history_read.list_months(db)


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(db: HistoryDb, run_id: int) -> dict[str, Any]:
    """Show one run with its slots, its steps and its technical log lines."""
    run = history_read.get_run(db, run_id)
    if run is None:
        raise NotFoundError(f"No run {run_id}")
    return run


@router.get("/events", response_model=list[Step])
def list_events(
    db: HistoryDb,
    category: Optional[Category] = None,
    before: Optional[int] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = history_read.DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """List activity log steps newest first, of runs and of the app; ``before`` pages back."""
    return history_read.list_events(db, category=category, before=before, limit=limit)
