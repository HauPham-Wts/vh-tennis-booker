"""Device setup route: the checks; runs and the schedule fix what they need themselves."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from fastapi import APIRouter
from pydantic import BaseModel

from court_booker import device_setup
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
