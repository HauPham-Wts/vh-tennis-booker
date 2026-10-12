"""Runtime configuration with defaults and optional TOML overrides."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from court_booker.errors import RequestError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

DEFAULT_MUMU_MANAGER = "C:/Program Files/Netease/MuMuPlayer/nx_main/MuMuManager.exe"


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
    prev_month: str = "Tháng trước"
    next_month: str = "Tháng sau"
    agree: str = "Tôi đã hiểu"
    fully_booked: str = "Hết chỗ"


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
    timeout: float = 10.0
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
    """Time server used to correct the PC clock before a timed start; empty disables."""
    open_retry_seconds: float = 60.0
    """How long to keep reloading the calendar while the date or slot is not open yet."""
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


def _apply_labels(labels: Labels, values: dict[str, str]) -> None:
    for key, value in values.items():
        attr = "continue_" if key == "continue" else key
        if not hasattr(labels, attr):
            raise ConfigError(f"Unknown label: {key!r}")
        setattr(labels, attr, value)
