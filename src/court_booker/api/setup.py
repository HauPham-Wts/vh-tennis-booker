"""Device setup routes: the checks, and auto setup."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from fastapi import APIRouter
from pydantic import BaseModel

from court_booker import device_setup
from court_booker.api.activity import open_store, reporter
from court_booker.api.context import Context
from court_booker.device_setup import Check, Status

router = APIRouter(prefix="/api", tags=["setup"])


class SetupItem(BaseModel):
    """One setup item; ``item`` and ``status`` are message keys of the UI."""

    item: str
    status: Status
    detail: str


def items(results: list[Check]) -> list[SetupItem]:
    return [SetupItem(item=r.item, status=r.status, detail=r.detail) for r in results]


@router.get("/setup", response_model=list[SetupItem])
def check_setup(context: Context) -> list[SetupItem]:
    """Check every setup item; nothing is changed."""
    config = context.config()
    return items(device_setup.run_checks(config, device_setup.find_tools(config)))


class AutoSetupRequest(BaseModel):
    """``restart_mumu`` allows restarting a running MuMu to apply its new screen."""

    restart_mumu: bool = False


@router.post("/setup/auto", response_model=list[SetupItem])
def run_auto_setup(context: Context, request: AutoSetupRequest) -> list[SetupItem]:
    """Fix every item auto setup can fix, holding the run lock, and record each item.

    Refused (400 ``bad_request``) from the wake time to 5 minutes after the start time,
    and (409 ``lock_held``) while a run holds the lock.
    """
    config = context.config()
    store = open_store(context)
    try:
        results = device_setup.run_auto_setup(
            config,
            context.config_path,
            device_setup.find_tools(config),
            context.data.lock,
            reporter(store),
            restart_mumu=request.restart_mumu,
        )
    finally:
        if store is not None:
            store.close()
    return items(results)
