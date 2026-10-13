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
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from court_booker.emulator import MuMu
from court_booker.errors import EmulatorError

logger = logging.getLogger(__name__)

# Item keys are stable: the app uses them as message keys.
MUMU_INSTALLED = "mumu_installed"
MUMU_SCREEN = "mumu_screen"

SCREEN = {"resolution_width": 540, "resolution_height": 1600, "resolution_dpi": 220}
"""The screen the booking flow is tuned for (spec 0.3.0): all slots fit without scrolling."""
SCREEN_SETTINGS = {
    "resolution_mode": "custom",
    "resolution_width.custom": "540",
    "resolution_height.custom": "1600",
    "resolution_dpi.custom": "220",
}
"""The MuMu settings that give :data:`SCREEN`."""

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
