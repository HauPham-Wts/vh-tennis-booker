"""Device setup: check the PC and the emulator, and fix what the code can fix.

This is the "Thiết lập máy" (device setup) tab of the app (spec part 6). The user installs
MuMu Player and the Vinhomes app and logs in; the checks find them and the app shows a guide
for anything missing. Auto setup does the rest: remember where MuMu is, set its screen to
540x1600 at 220 DPI and allow wake timers. Whether the app is logged in shows in the dry run
(exit code 4), which the schedule requires anyway, so it is not checked here.
"""

from __future__ import annotations

import itertools
import logging
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from court_booker.adb import AUTO, Adb, find_adb, resolve_device
from court_booker.config import Config, ConfigError, save_config
from court_booker.emulator import MuMu, Run, run_command
from court_booker.errors import AdbNotFoundError, DeviceError, EmulatorError

logger = logging.getLogger(__name__)

# Item keys are stable: the app uses them as message keys.
MUMU_INSTALLED = "mumu_installed"
MUMU_SCREEN = "mumu_screen"
WAKE_TIMERS = "wake_timers"
APP_INSTALLED = "app_installed"

SCREEN = {"resolution_width": 540, "resolution_height": 1600, "resolution_dpi": 220}
"""The screen the booking flow is tuned for (spec 0.3.0): all slots fit without scrolling."""
SCREEN_SETTINGS = {
    "resolution_mode": "custom",
    "resolution_width.custom": "540",
    "resolution_height.custom": "1600",
    "resolution_dpi.custom": "220",
}
"""The MuMu settings that give :data:`SCREEN`."""

WAKE_SETTING = ("SCHEME_CURRENT", "SUB_SLEEP", "RTCWAKE")
"""``powercfg`` names of "Allow wake timers" in the active power plan."""
WAKE_ENABLED = 1
_WAKE_NAMES = {0: "disabled", 1: "enabled", 2: "important only"}

_MANAGER_LAYOUTS = (Path("nx_main") / "MuMuManager.exe", Path("shell") / "MuMuManager.exe")
"""Where MuMuManager.exe sits in an install folder (MuMu Player 12 and older)."""
DEFAULT_FOLDERS = (
    Path("C:/Program Files/Netease/MuMuPlayer"),
    Path("C:/Program Files/Netease/MuMuPlayerGlobal-12.0"),
    Path("C:/Program Files/Netease/MuMu Player 12"),
)
_UNINSTALL_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
_UNINSTALL_KEY_32 = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"


class Status(str, Enum):
    """The state of one setup item; the value is stable, like an event kind."""

    OK = "ok"
    """Already right."""
    FIXED = "fixed"
    """Auto setup just made it right."""
    FIXABLE = "fixable"
    """Not right; auto setup can fix it."""
    USER = "user"
    """Only the user can fix it (install, log in); the app shows a guide."""
    UNKNOWN = "unknown"
    """Cannot be told now, e.g. while MuMu is not running."""


@dataclass(frozen=True)
class Check:
    """The result for one setup item; ``detail`` is for the log."""

    item: str
    status: Status
    detail: str


def installed_folders() -> list[Path]:
    """Return the MuMu install folders listed in the Windows uninstall registry."""
    if sys.platform != "win32":
        return []
    import winreg

    folders = []
    roots = (
        (winreg.HKEY_LOCAL_MACHINE, _UNINSTALL_KEY),
        (winreg.HKEY_LOCAL_MACHINE, _UNINSTALL_KEY_32),
        (winreg.HKEY_CURRENT_USER, _UNINSTALL_KEY),
    )
    for hive, path in roots:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            continue
        with root:
            for index in itertools.count():
                try:
                    name = winreg.EnumKey(root, index)
                except OSError:  # no more entries
                    break
                try:
                    with winreg.OpenKey(root, name) as entry:
                        display = winreg.QueryValueEx(entry, "DisplayName")[0]
                        location = winreg.QueryValueEx(entry, "InstallLocation")[0]
                except OSError:
                    continue
                if isinstance(display, str) and "mumu" in display.lower() and location:
                    folders.append(Path(location))
    return folders


def find_mumu_manager(configured: str, folders: Iterable[Path] | None = None) -> Path | None:
    """Return MuMuManager.exe: the configured one, else one in an install folder.

    ``folders`` defaults to the folders in the uninstall registry, then the usual ones.
    """
    if configured and Path(configured).is_file():
        return Path(configured)
    if folders is None:
        folders = [*installed_folders(), *DEFAULT_FOLDERS]
    for folder in folders:
        for layout in _MANAGER_LAYOUTS:
            if (folder / layout).is_file():
                return folder / layout
    return None


def check_mumu(manager: Path | None, configured: str) -> Check:
    """Check that MuMu is installed and that the config points at it."""
    if manager is None:
        return Check(MUMU_INSTALLED, Status.USER, "MuMu Player not found; install it")
    if not configured or Path(configured) != manager:
        return Check(
            MUMU_INSTALLED,
            Status.FIXABLE,
            f"MuMu found at {manager}; the config has {configured or 'no path'}",
        )
    return Check(MUMU_INSTALLED, Status.OK, f"MuMu at {manager}")


def check_screen(mumu: MuMu | None) -> Check:
    """Check that the MuMu instance uses :data:`SCREEN`; readable while MuMu is off."""
    if mumu is None:
        return Check(MUMU_SCREEN, Status.UNKNOWN, "MuMu not found")
    try:
        values = mumu.settings(*SCREEN)
        actual = {key: round(float(values[key])) for key in SCREEN}
    except (EmulatorError, KeyError, ValueError) as exc:
        return Check(MUMU_SCREEN, Status.UNKNOWN, f"Could not read the MuMu screen: {exc}")
    shown = (
        f"{actual['resolution_width']}x{actual['resolution_height']}"
        f" at {actual['resolution_dpi']} DPI"
    )
    if actual == SCREEN:
        return Check(MUMU_SCREEN, Status.OK, f"Screen {shown}")
    return Check(MUMU_SCREEN, Status.FIXABLE, f"Screen {shown}; booking needs 540x1600 at 220 DPI")


def wake_timer_indexes(output: str) -> tuple[int, int] | None:
    """Return the plugged-in and on-battery values of "Allow wake timers".

    ``output`` is ``powercfg /query``'s. Its labels follow the Windows language, so the two
    hexadecimal values are read by position: plugged in (AC), then on battery (DC).
    """
    values = re.findall(r"0x([0-9a-fA-F]{8})", output)
    if len(values) < 2:
        return None
    return int(values[-2], 16), int(values[-1], 16)


def check_wake_timers(run: Run = run_command) -> Check:
    """Check that wake timers may wake the PC, plugged in and on battery."""
    try:
        result = run(["powercfg", "/query", *WAKE_SETTING])
    except (OSError, subprocess.SubprocessError) as exc:
        return Check(WAKE_TIMERS, Status.UNKNOWN, f"powercfg could not run: {exc}")
    indexes = wake_timer_indexes(result.stdout) if result.returncode == 0 else None
    if indexes is None:
        return Check(WAKE_TIMERS, Status.UNKNOWN, "powercfg did not report wake timers")
    plugged, battery = indexes
    detail = (
        f"Wake timers {_WAKE_NAMES.get(plugged, plugged)} plugged in,"
        f" {_WAKE_NAMES.get(battery, battery)} on battery"
    )
    if plugged == battery == WAKE_ENABLED:
        return Check(WAKE_TIMERS, Status.OK, detail)
    return Check(WAKE_TIMERS, Status.FIXABLE, detail)


def check_app(mumu: MuMu | None, adb: Adb | None, package: str) -> Check:
    """Check that ``package`` is installed in MuMu; MuMu must be running to tell."""
    if mumu is None or adb is None:
        return Check(APP_INSTALLED, Status.UNKNOWN, "MuMu or adb not found")
    try:
        if not mumu.is_started():
            return Check(APP_INSTALLED, Status.UNKNOWN, "Start MuMu to check the app")
        serial = resolve_device(adb, AUTO, mumu.adb_serial())
        output = adb.shell(serial, "pm", "path", package)
    except DeviceError as exc:
        return Check(APP_INSTALLED, Status.UNKNOWN, f"Could not ask MuMu: {exc}")
    if "package:" in output:
        return Check(APP_INSTALLED, Status.OK, f"{package} installed")
    return Check(APP_INSTALLED, Status.USER, f"{package} is not installed in MuMu")


@dataclass(frozen=True)
class Tools:
    """What the checks look at: MuMuManager.exe, the MuMu instance and adb, where found."""

    manager: Path | None
    mumu: MuMu | None
    adb: Adb | None


def find_tools(config: Config) -> Tools:
    """Find MuMu and adb as a run would, without starting anything."""
    manager = find_mumu_manager(config.mumu_manager)
    mumu = MuMu(manager, config.mumu_index) if manager else None
    try:
        adb = Adb(find_adb(config.adb_path, [manager.parent] if manager else []))
    except AdbNotFoundError:
        adb = None
    return Tools(manager, mumu, adb)


def run_checks(config: Config, tools: Tools, run: Run = run_command) -> list[Check]:
    """Check every setup item; nothing is changed."""
    return [
        check_mumu(tools.manager, config.mumu_manager),
        check_screen(tools.mumu),
        check_wake_timers(run),
        check_app(tools.mumu, tools.adb, config.package),
    ]


def auto_setup(
    config: Config,
    config_path: Path,
    tools: Tools,
    *,
    restart_mumu: bool = False,
    run: Run = run_command,
) -> list[Check]:
    """Fix every item auto setup can fix, and return the result of each item.

    A running MuMu applies a new screen only after a restart, which happens only with
    ``restart_mumu``. Saving the MuMu path rewrites the config file without its comments.
    """
    results = []
    for check in run_checks(config, tools, run):
        if check.status is Status.FIXABLE:
            if check.item == MUMU_INSTALLED:
                check = _save_mumu_path(config, config_path, tools)
            elif check.item == MUMU_SCREEN:
                check = _set_screen(tools, restart_mumu)
            elif check.item == WAKE_TIMERS:
                check = _allow_wake_timers(run)
        logger.info("Setup %s: %s (%s)", check.item, check.status.value, check.detail)
        results.append(check)
    return results


def _save_mumu_path(config: Config, config_path: Path, tools: Tools) -> Check:
    try:
        save_config(replace(config, mumu_manager=str(tools.manager)), config_path)
    except (ConfigError, OSError) as exc:
        return Check(MUMU_INSTALLED, Status.USER, f"Could not save the config: {exc}")
    return Check(MUMU_INSTALLED, Status.FIXED, f"Saved the MuMu path {tools.manager}")


def _set_screen(tools: Tools, restart_mumu: bool) -> Check:
    if tools.mumu is None:
        return Check(MUMU_SCREEN, Status.UNKNOWN, "MuMu not found")
    try:
        running = tools.mumu.is_started()
        if running and not restart_mumu:
            return Check(
                MUMU_SCREEN, Status.FIXABLE, "MuMu is running; allow a restart to set its screen"
            )
        tools.mumu.change_settings(SCREEN_SETTINGS)
        written = tools.mumu.settings(*SCREEN_SETTINGS)
        if running:
            tools.mumu.restart()
    except EmulatorError as exc:
        return Check(MUMU_SCREEN, Status.USER, f"Could not set the MuMu screen: {exc}")
    if not all(_same(written.get(key), value) for key, value in SCREEN_SETTINGS.items()):
        return Check(MUMU_SCREEN, Status.USER, f"MuMu kept its screen settings: {written}")
    when = "MuMu restarted" if running else "applies when MuMu starts"
    return Check(MUMU_SCREEN, Status.FIXED, f"Screen set to 540x1600 at 220 DPI; {when}")


def _same(actual: str | None, wanted: str) -> bool:
    """Compare a MuMu setting as text or as a number (MuMu writes ``540.000000``)."""
    if actual == wanted:
        return True
    try:
        return actual is not None and float(actual) == float(wanted)
    except ValueError:
        return False


def _allow_wake_timers(run: Run) -> Check:
    commands = (
        ["powercfg", "/setacvalueindex", *WAKE_SETTING, str(WAKE_ENABLED)],
        ["powercfg", "/setdcvalueindex", *WAKE_SETTING, str(WAKE_ENABLED)],
        ["powercfg", "/setactive", WAKE_SETTING[0]],
    )
    for command in commands:
        try:
            result = run(command)
        except (OSError, subprocess.SubprocessError) as exc:
            return Check(WAKE_TIMERS, Status.USER, f"powercfg could not run: {exc}")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            return Check(WAKE_TIMERS, Status.USER, f"powercfg {command[1]} failed: {detail}")
    after = check_wake_timers(run)
    if after.status is Status.OK:
        return Check(WAKE_TIMERS, Status.FIXED, after.detail)
    return Check(WAKE_TIMERS, Status.USER, after.detail)
