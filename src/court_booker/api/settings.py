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
    INSTANCE_KEYS,
    Config,
    config_from_dict,
    config_to_dict,
    instance_config,
    save_config,
    validate_config,
)
from court_booker.events import EventKind

router = APIRouter(prefix="/api", tags=["settings"])

HIDDEN = ("telegram_token", "telegram_chat_id", "windows_notification", "notification_language")
"""Config keys these routes neither show nor change: the Telegram summary is set up by hand,
and the Windows notification is not a booking setting."""


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
    venue_list: str
    court_list: str
    residents: str
    notice: str
    quota_full: str
    booked_time: str
    booked_place: str
    ticket: str
    processing: str
    registered: str


class InstanceSettings(BaseModel):
    """The booking settings of another MuMu instance, which books with its own account."""

    model_config = ConfigDict(extra="forbid")

    mumu_index: int
    slots: list[str]
    subdivision: str
    sport: str
    court: str
    venue_keyword: str


class Settings(BaseModel):
    """Every booking setting; the UI changes the slots, subdivision, sport and court, and sends
    the rest back."""

    model_config = ConfigDict(extra="forbid")

    slots: list[str]
    subdivision: str
    """The account's subdivision, ``origami`` or ``bs``; empty leaves it to the account."""
    sport: str
    """What to book: ``tennis``, ``multi``, ``volleyball``, ``table-tennis``, ``basketball``,
    ``football``, ``pickleball`` or ``badminton``."""
    court: str
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
    instances: list[InstanceSettings]
    """Other MuMu instances with all their settings; the app changes them, never which
    instances there are (each needs its own MuMu instance and account set up first)."""
    labels: LabelSettings


def settings_of(config: Config) -> dict[str, Any]:
    """Return ``config`` as the settings the app shows: TOML keys, without hidden ones."""
    data = config_to_dict(config)
    for key in HIDDEN:
        data.pop(key)
    # Each instance in full, with the settings it takes from the top of the file.
    data["instances"] = [
        {key: getattr(instance_config(config, table), key) for key in INSTANCE_KEYS}
        for table in config.instances
    ]
    return data


@router.get("/settings", response_model=Settings)
def read_settings(context: Context) -> dict[str, Any]:
    """Read the settings the next run will use."""
    return settings_of(context.config())


@router.put("/settings", response_model=Settings)
def save_settings(context: Context, settings: Settings) -> dict[str, Any]:
    """Check and save the settings; they apply from the next run.

    Invalid settings are refused with every problem listed, and the file is left as it
    was. The file is rewritten without its comments; the hidden keys are kept.
    """
    old = context.config()
    config = config_from_dict({**config_to_dict(old), **settings.model_dump(by_alias=True)})
    problems = validate_config(config)
    if _indexes(config) != _indexes(old):
        problems.append("MuMu instances are added or removed in config.toml, not here")
    if problems:
        raise InvalidSettingsError(problems)
    before, after = settings_of(old), settings_of(config)
    changed = sorted(key for key in after if after[key] != before[key])
    if changed:
        save_config(config, context.config_path)
        record(context, EventKind.SETTINGS_SAVED, changed=changed)
    return after


def _indexes(config: Config) -> list[Any]:
    return [table.get("mumu_index") for table in config.instances]
