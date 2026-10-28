"""Accounts route: the subdivision each MuMu instance's account last told.

The subdivisions, sports and courts themselves reach the UI as ``ui/src/catalog.json``,
written from :mod:`court_booker.catalog` by ``tools/export_openapi.py``.
"""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from court_booker import catalog, history_read
from court_booker.api.history import HistoryDb

router = APIRouter(prefix="/api", tags=["accounts"])


class AccountSubdivision(BaseModel):
    """The subdivision a MuMu instance's account last told, read from its home screen."""

    device: Optional[int]
    """The MuMu instance; ``None`` for a run of a version before 0.13.0."""
    subdivision: str
    """One of the catalog's subdivisions; one it no longer lists is left out."""
    seen_at: str


@router.get("/accounts", response_model=list[AccountSubdivision])
def read_accounts(db: HistoryDb) -> list[dict[str, Any]]:
    """Read the subdivision each MuMu instance's account told last, newest first."""
    return [
        account
        for account in history_read.account_subdivisions(db)
        if catalog.subdivision(account["subdivision"] or "") is not None
    ]
