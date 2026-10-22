"""Runtime configuration with defaults and optional TOML overrides."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import tomli_w

from court_booker.clock import parse_time
from court_booker.errors import RequestError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

DEFAULT_MUMU_MANAGER = "C:/Program Files/Netease/MuMuPlayer/nx_main/MuMuManager.exe"
MAX_DAYS_AHEAD = 2
"""The app books from today to today + 2."""
WARM_UP_RANGE = (5, 600)
"""Allowed ``warm_up_seconds``: time to load the utilities list, at most ten minutes ahead."""
_SLOT_PATTERN = re.compile(r"\d{2}:\d{2} - \d{2}:\d{2}")


@dataclass
class Labels:
    """Accessibility labels shown by the app.

    These are UI strings of the target app, not project text, and therefore
    stay in the app's language.
    """

    home: str = "Tiện ích"
    utility: str = "Sân Tennis"
    continue_: str = "Tiếp tục"
    confirm: str = "Xác nhận"
    confirm_page: str = "Xác nhận đăng ký"
    """Title of the confirmation page. Unused since the ticket tells success (0.6.2); kept
    so a config that sets it still loads."""
    prev_month: str = "Tháng trước"
    next_month: str = "Tháng sau"
    agree: str = "Tôi đã hiểu"
    fully_booked: str = "Hết chỗ"
    notice: str = "Thông báo"
    """Title of the app's message dialogs, e.g. the monthly quota or a refused booking."""
    booked_time: str = "Thời gian đặt lịch"
    """Caption of the date and slot on the confirmation page and the ticket."""
    booked_place: str = "Vị trí/dịch vụ"
    """Caption of the court on the confirmation page and the ticket."""
    ticket: str = "Chi tiết đặt lịch"
    """Title of the ticket screen that follows "Xác nhận"."""
    processing: str = "Đang xử lý"
    """Ticket status while the server handles the booking (seen at 06:00)."""
    registered: str = "Đã đăng ký"
    """Ticket status once the booking is registered."""


@dataclass
class Config:
    """Booking settings."""

    device: str = "auto"
    """ADB serial, or ``auto`` to use the emulator's own serial or scan for one."""
    adb_path: str = ""
    """adb executable; empty searches PATH, then the emulator folder."""
    package: str = "com.vinhomes.resident"
    days_ahead: int = 2
    slots: list[str] = field(default_factory=lambda: ["11:00 - 12:00", "14:00 - 15:00"])
    court: str = "S10 - Sân tennis"
    venue_keyword: str = "Origami"
    timeout: float = 30.0
    """Longest wait for any screen, in seconds; one that shows sooner is acted on at once.

    No step of a booking by hand ever took 30 s, also on busy days (user, 2026-10-19); the
    ticket once took over 10 s after "Xác nhận" (2026-10-19, 10:03)."""
    max_swipes: int = 6
    mumu_manager: str = DEFAULT_MUMU_MANAGER
    """MuMuManager.exe used to start the emulator; empty skips starting it."""
    mumu_index: int = 0
    boot_timeout: float = 180.0
    """Seconds to wait for the emulator to boot and for the app to open."""
    restart_app: bool = True
    """Stop and start the app before booking instead of reusing its current screen."""
    start_at: str = "06:00"
    """Booking opening time (HH:MM or HH:MM:SS), used by ``--scheduled``."""
    wake_at: str = "05:45"
    """When the scheduled task wakes the PC and starts preparing; before ``start_at``."""
    ntp_server: str = "time.google.com"
    """Time server for the run's clock; does not set Windows time. Empty uses the PC clock."""
    open_retry_seconds: float = 60.0
    """How long to keep reloading the calendar while the date or slot is not open yet."""
    warm_up_seconds: float = 60.0
    """How long before ``start_at`` a timed run leaves the home screen for the utilities list."""
    log_dir: str = "logs"
    """Folder for daily log files, relative to the config file; empty disables them."""
    telegram_token: str = ""
    """Bot token from @BotFather; with ``telegram_chat_id`` the summary is sent there."""
    telegram_chat_id: str = ""
    next_month_xy: tuple[float, float] = (0.953, 0.122)
    """Fallback tap position (screen ratio) when the next-month button has no label."""
    prev_month_xy: tuple[float, float] = (0.873, 0.122)
    """Fallback tap position (screen ratio) when the previous-month button has no label."""
    labels: Labels = field(default_factory=Labels)


class ConfigError(RequestError, ValueError):
    """The configuration file contains an unknown key or an invalid value."""


def load_config(path: str | Path | None) -> Config:
    """Return the default configuration overridden by ``path`` if it exists."""
    if path is None or not Path(path).exists():
        return Config()
    return config_from_dict(tomllib.loads(Path(path).read_text(encoding="utf-8")))


def config_from_dict(data: dict[str, Any]) -> Config:
    """Return the default configuration overridden by ``data``, a parsed TOML document."""
    config = Config()
    known_keys = {f.name for f in fields(Config)} - {"labels"}

    for key, value in data.items():
        if key == "labels":
            _apply_labels(config.labels, value)
        elif key in known_keys:
            setattr(config, key, tuple(value) if key.endswith("_xy") else value)
        else:
            raise ConfigError(f"Unknown configuration key: {key!r}")
    return config


def config_to_dict(config: Config) -> dict[str, Any]:
    """Return ``config`` as a TOML document: every key, with the labels as a table."""
    data: dict[str, Any] = {}
    for item in fields(Config):
        if item.name != "labels":
            value = getattr(config, item.name)
            data[item.name] = list(value) if isinstance(value, tuple) else value
    data["labels"] = {
        ("continue" if item.name == "continue_" else item.name): getattr(config.labels, item.name)
        for item in fields(Labels)
    }
    return data


def save_config(config: Config, path: str | Path) -> None:
    """Validate ``config`` and write it to ``path`` as TOML.

    The text goes to a temporary file that then replaces ``path``, so a run reading the
    file at that moment sees the old or the new version, never half of one. Comments of
    an existing file are not kept. Only the labels that differ from the defaults are
    written: a runner of an older version refuses a label it does not know, and a later
    version's fix to a default label then reaches this file too.
    """
    problems = validate_config(config)
    if problems:
        raise ConfigError("; ".join(problems))
    data = config_to_dict(config)
    defaults = config_to_dict(Config())["labels"]
    labels = {key: value for key, value in data.pop("labels").items() if value != defaults[key]}
    if labels:
        data["labels"] = labels
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(tomli_w.dumps(data), encoding="utf-8")
    os.replace(temporary, target)


def ensure_config(path: str | Path) -> Path:
    """Write the default config to ``path`` unless a file is already there."""
    target = Path(path)
    if not target.exists():
        save_config(Config(), target)
    return target


def validate_config(config: Config) -> list[str]:
    """Return what is wrong with ``config`` for booking, or an empty list.

    Used before saving, so a bad edit never reaches the file the 06:00 run reads.
    """
    problems = []
    if not config.slots:
        problems.append("choose at least one slot")
    for slot in config.slots:
        if not isinstance(slot, str) or not _SLOT_PATTERN.fullmatch(slot):
            problems.append(f"slot {slot!r} must look like '18:00 - 19:00'")
    if len(set(config.slots)) != len(config.slots):
        problems.append("a slot is listed twice")
    if not config.court.strip():
        problems.append("court is empty")
    if not 0 <= config.days_ahead <= MAX_DAYS_AHEAD:
        problems.append(f"days_ahead must be 0 to {MAX_DAYS_AHEAD}")
    times = {}
    for name in ("wake_at", "start_at"):
        try:
            times[name] = parse_time(getattr(config, name), name)
        except RequestError as exc:
            problems.append(str(exc))
    if len(times) == 2 and times["wake_at"] >= times["start_at"]:
        problems.append("wake_at must be before start_at")
    for name in ("timeout", "boot_timeout"):
        if getattr(config, name) <= 0:
            problems.append(f"{name} must be positive")
    for name in ("open_retry_seconds", "max_swipes"):
        if getattr(config, name) < 0:
            problems.append(f"{name} must not be negative")
    if not WARM_UP_RANGE[0] <= config.warm_up_seconds <= WARM_UP_RANGE[1]:
        problems.append(f"warm_up_seconds must be {WARM_UP_RANGE[0]} to {WARM_UP_RANGE[1]} seconds")
    for name in ("next_month_xy", "prev_month_xy"):
        point = getattr(config, name)
        if len(point) != 2 or not all(0 <= value <= 1 for value in point):
            problems.append(f"{name} must be two screen ratios between 0 and 1")
    return problems


def _apply_labels(labels: Labels, values: dict[str, str]) -> None:
    for key, value in values.items():
        attr = "continue_" if key == "continue" else key
        if not hasattr(labels, attr):
            raise ConfigError(f"Unknown label: {key!r}")
        setattr(labels, attr, value)
