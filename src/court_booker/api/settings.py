"""Settings routes: the booking settings of ``config.toml``, read and saved."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from court_booker.api.activity import record
from court_booker.api.context import Context
from court_booker.api.errors import InvalidSettingsError
from court_booker.config import (
    Config,
    config_from_dict,
    config_to_dict,
    save_config,
    validate_config,
)
from court_booker.events import EventKind

router = APIRouter(prefix="/api", tags=["settings"])

HIDDEN = ("telegram_token", "telegram_chat_id")
"""Config keys the app neither shows nor changes (the Telegram summary is set up by hand)."""


class LabelSettings(BaseModel):
    """Accessibility labels of the Vinhomes app, in its language."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    home: str
    utility: str
    continue_: str = Field(alias="continue")
    confirm: str
    confirm_page: str
    prev_month: str
    next_month: str
    agree: str
    fully_booked: str
    notice: str


class Settings(BaseModel):
    """Every booking setting; the UI shows the first five, the rest under "Advanced"."""

    model_config = ConfigDict(extra="forbid")

    slots: list[str]
    court: str
    days_ahead: int
    wake_at: str
    start_at: str
    venue_keyword: str
    device: str
    adb_path: str
    package: str
    timeout: float
    max_swipes: int
    mumu_manager: str
    mumu_index: int
    boot_timeout: float
    restart_app: bool
    ntp_server: str
    open_retry_seconds: float
    warm_up_seconds: float
    log_dir: str
    next_month_xy: tuple[float, float]
    prev_month_xy: tuple[float, float]
    labels: LabelSettings


def settings_of(config: Config) -> dict[str, Any]:
    """Return ``config`` as the settings the app shows: TOML keys, without hidden ones."""
    data = config_to_dict(config)
    for key in HIDDEN:
        data.pop(key)
    return data


@router.get("/settings", response_model=Settings)
def read_settings(context: Context) -> dict[str, Any]:
    """Read the settings the next run will use."""
    return settings_of(context.config())


@router.put("/settings", response_model=Settings)
def save_settings(context: Context, settings: Settings) -> dict[str, Any]:
    """Check and save the settings; they apply from the next run.

    Invalid settings are refused with every problem listed, and the file is left as it
    was. The file is rewritten without its comments; the hidden Telegram keys are kept.
    """
    old = context.config()
    config = config_from_dict({**config_to_dict(old), **settings.model_dump(by_alias=True)})
    problems = validate_config(config)
    if problems:
        raise InvalidSettingsError(problems)
    before, after = settings_of(old), settings_of(config)
    changed = sorted(key for key in after if after[key] != before[key])
    if changed:
        save_config(config, context.config_path)
        record(context, EventKind.SETTINGS_SAVED, changed=changed)
    return after
