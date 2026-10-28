"""Runtime configuration with defaults and optional TOML overrides."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

import tomli_w

from court_booker import catalog
from court_booker.clock import parse_time
from court_booker.errors import RequestError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

DEFAULT_MUMU_MANAGER = "C:/Program Files/Netease/MuMuPlayer/nx_main/MuMuManager.exe"
DAYS_AHEAD = 2
"""The run books today + 2: the newest day, which the app opens for booking at 06:00."""
WARM_UP_RANGE = (5, 600)
"""Allowed ``warm_up_seconds``: time to load the utilities list, at most ten minutes ahead."""
NOTIFICATION_LANGUAGES = ("vi", "en")
"""Languages of the Windows notification: those of the app's own interface."""
SPORTS = {
    "tennis": "Sân Tennis",
    "multi": "Sân đa năng",
    "volleyball": "Sân bóng chuyền",
    "table-tennis": "Sân bóng bàn",
    "basketball": "Sân bóng rổ",
    "football": "Sân bóng đá",
    "pickleball": "Sân Pickleball",
    "badminton": "Sân cầu lông",
}
"""The sports the run books, each with its tile on the utilities list in Vietnamese (field
notes, "Other sports"); the English tiles are in :mod:`court_booker.app_language`."""
INSTANCE_KEYS = ("mumu_index", "slots", "subdivision", "sport", "court", "venue_keyword")
"""Keys of an ``[[instances]]`` table: the booking settings of another MuMu instance, which
books with its own account; ``mumu_index`` is required, the others default to the file's."""
_IGNORED_KEYS = ("days_ahead",)
"""Keys of older files, read and dropped: the play day was a setting until 0.13.1."""
_WRITTEN_WHEN_CHANGED = (
    "windows_notification",
    "notification_language",
    "instances",
    "sport",
    "subdivision",
)
"""Keys ``save_config`` writes only when they differ from the default (see there)."""
_INHERITED_KEYS = ("sport", "subdivision")
"""Keys of :data:`_WRITTEN_WHEN_CHANGED` an instance table drops when they equal the file's."""
_SLOT_PATTERN = re.compile(r"\d{2}:\d{2} - \d{2}:\d{2}")


@dataclass
class Labels:
    """Accessibility labels shown by the app.

    These are UI strings of the target app, not project text, and therefore
    stay in the app's language.
    """

    home: str = "Tiện ích"
    utility: str = ""
    """Tile of the utility to book on the utilities list; empty for the tile of ``sport``."""
    continue_: str = "Tiếp tục"
    confirm: str = "Xác nhận"
    confirm_page: str = "Xác nhận đăng ký"
    """Title of the confirmation page. Unused since the ticket tells success (0.6.2); kept
    so a config that sets it still loads."""
    prev_month: str = "Tháng trước"
    next_month: str = "Tháng sau"
    agree: str = "Tôi đã hiểu"
    fully_booked: str = "Hết chỗ"
    venue_list: str = "Chọn phân khu"
    """Heading of the venues the app may list before the courts."""
    court_list: str = "Chọn vị trí/dịch vụ"
    """Heading of the court list."""
    residents: str = "Số lượng cư dân"
    """Caption of the booking details page that follows the court list."""
    notice: str = "Thông báo"
    """Title of the app's message dialogs, e.g. the monthly quota or a refused booking."""
    quota_full: str = "hết hạn mức"
    """Part of the message of the notice that the apartment's quota is used up: "Căn hộ đã hết
    hạn mức đăng ký tiện ích cho phép." No later round of the run can book then."""
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
    slots: list[str] = field(default_factory=lambda: ["11:00 - 12:00", "14:00 - 15:00"])
    subdivision: str = ""
    """The account's subdivision, one of :data:`court_booker.catalog.SUBDIVISIONS`; empty
    leaves it to the account. Filters the choices of the app; the run books by ``court``."""
    sport: str = "tennis"
    """What to book, one of :data:`SPORTS`: the tile tapped on the utilities list."""
    court: str = "S10 - Sân tennis"
    venue_keyword: str = "Origami"
    """Picks the venue of a court not in :mod:`court_booker.catalog` when the app lists
    several; a court in the catalog takes its own venue, a single venue is tapped whatever its
    name."""
    timeout: float = 30.0
    """Longest wait for any screen, in seconds; one that shows sooner is acted on at once.

    No step of a booking by hand ever took 30 s, also on busy days (user, 2026-10-19); the
    ticket once took over 10 s after "Xác nhận" (2026-10-19, 10:03)."""
    max_swipes: int = 6
    """Swipes allowed to bring a hidden slot into view."""
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
    windows_notification: bool = True
    """Show the outcome of every run, dry runs too, as a Windows notification."""
    notification_language: str = "vi"
    """Language of the Windows notification, one of :data:`NOTIFICATION_LANGUAGES`."""
    next_month_xy: tuple[float, float] = (0.930, 0.122)
    """Fallback tap position (screen ratio) when the next-month button has no label."""
    prev_month_xy: tuple[float, float] = (0.807, 0.122)
    """Fallback tap position (screen ratio) when the previous-month button has no label."""
    instances: list[dict[str, Any]] = field(default_factory=list)
    """Other MuMu instances, each logged in to its own account and booking with its own
    settings (:data:`INSTANCE_KEYS`) in a process of its own, side by side with this one."""
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
        elif key == "instances":
            config.instances = _instance_tables(value)
        elif key in known_keys:
            setattr(config, key, tuple(value) if key.endswith("_xy") else value)
        elif key not in _IGNORED_KEYS:
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
    version's fix to a default label then reaches this file too. For the same reason the
    keys of :data:`_WRITTEN_WHEN_CHANGED`, added after 0.9.1, are written only when changed,
    and an instance's ``sport`` and ``subdivision`` only when they differ from the file's.
    """
    problems = validate_config(config)
    if problems:
        raise ConfigError("; ".join(problems))
    data = config_to_dict(config)
    data["instances"] = [
        {
            key: value
            for key, value in table.items()
            if key not in _INHERITED_KEYS or value != getattr(config, key)
        }
        for table in config.instances
    ]
    defaults = config_to_dict(Config())
    for key in _WRITTEN_WHEN_CHANGED:
        if data[key] == defaults[key]:
            del data[key]
    labels = {
        key: value for key, value in data.pop("labels").items() if value != defaults["labels"][key]
    }
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
    if config.sport not in SPORTS:
        problems.append(f"sport must be one of {', '.join(SPORTS)}")
    if config.subdivision:
        chosen = catalog.subdivision(config.subdivision)
        if chosen is None:
            names = ", ".join(item.id for item in catalog.SUBDIVISIONS)
            problems.append(f"subdivision must be empty or one of {names}")
        elif config.sport in SPORTS and chosen.sport(config.sport) is None:
            problems.append(f"{chosen.name} has no {config.sport} courts")
    if not config.court.strip():
        problems.append("court is empty")
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
    if config.notification_language not in NOTIFICATION_LANGUAGES:
        problems.append(f"notification_language must be one of {', '.join(NOTIFICATION_LANGUAGES)}")
    for name in ("next_month_xy", "prev_month_xy"):
        point = getattr(config, name)
        if len(point) != 2 or not all(0 <= value <= 1 for value in point):
            problems.append(f"{name} must be two screen ratios between 0 and 1")
    if config.instances and (not config.mumu_manager or config.device != "auto"):
        problems.append('instances need mumu_manager and device = "auto"')
    indexes = [config.mumu_index]
    for table in config.instances:
        index = table.get("mumu_index")
        if not isinstance(index, int) or index < 0:
            problems.append(f"instance mumu_index {index!r} must be 0 or more")
        elif index in indexes:
            problems.append(f"MuMu instance {index} is listed twice")
        else:
            indexes.append(index)
            # Only its own problems: the shared settings are reported once, above.
            own = validate_config(instance_config(config, table))
            problems += [f"MuMu instance {index}: {item}" for item in own if item not in problems]
    return problems


def instance_config(config: Config, table: dict[str, Any]) -> Config:
    """Return the settings of the instance ``table`` describes: ``config`` with its keys."""
    return replace(config, **table, instances=[])


def _instance_tables(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(table, dict) for table in value):
        raise ConfigError("instances must be [[instances]] tables")
    tables = [
        {key: item for key, item in table.items() if key not in _IGNORED_KEYS} for table in value
    ]
    for table in tables:
        if "mumu_index" not in table:
            raise ConfigError("Each [[instances]] table needs mumu_index")
        unknown = sorted(set(table) - set(INSTANCE_KEYS))
        if unknown:
            raise ConfigError(f"Unknown key in [[instances]]: {unknown[0]!r}")
    return tables


def _apply_labels(labels: Labels, values: dict[str, str]) -> None:
    for key, value in values.items():
        attr = "continue_" if key == "continue" else key
        if not hasattr(labels, attr):
            raise ConfigError(f"Unknown label: {key!r}")
        setattr(labels, attr, value)
