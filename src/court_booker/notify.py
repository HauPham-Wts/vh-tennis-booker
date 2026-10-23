"""Report the outcome of a run: a Windows notification, and a Telegram summary if set up."""

from __future__ import annotations

import base64
import logging
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Sequence
from datetime import date
from typing import Callable
from xml.sax.saxutils import escape

from court_booker.runner import RoundResult

logger = logging.getLogger(__name__)

Post = Callable[[str, bytes], None]
Run = Callable[..., "subprocess.CompletedProcess[bytes]"]

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 10.0

APP_ID = "CourtBooker"
"""AppUserModelID the notifications come from; Windows shows its ``DisplayName``."""
APP_NAME = "Court Booker"
_WINDOWS_TIMEOUT = 20.0
"""Seconds PowerShell may take; it took 2.5 s on its first start of the day (2026-10-23)."""
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_STDERR_LOGGED = 300
"""Characters of PowerShell's error output kept in the log."""

# Registers the AppUserModelID under HKCU (no admin rights or shortcut needed), then shows
# the toast. The XML goes in a here-string, which ends only at a line starting with '@;
# _toast_xml escapes every apostrophe, so no text can end it early.
_SCRIPT = r"""$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'Stop'
$key = 'HKCU:\Software\Classes\AppUserModelId\{app_id}'
if (-not (Test-Path $key)) {{ New-Item -Path $key | Out-Null }}
Set-ItemProperty -Path $key -Name DisplayName -Value '{app_name}'
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml(@'
{xml}
'@)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app_id}').Show($toast)
"""  # noqa: E501

DEFAULT_LANGUAGE = "vi"
TEXTS = {
    "vi": {
        "title": "Đặt sân {day}: {outcome}",
        "booked": "{booked}/{total} thành công",
        "not_booked": "không đặt được",
        "stopped": "đã dừng",
        "dry_run": " (chạy thử)",
    },
    "en": {
        "title": "Courts for {day}: {outcome}",
        "booked": "{booked}/{total} booked",
        "not_booked": "not booked",
        "stopped": "stopped",
        "dry_run": " (dry run)",
    },
}
"""Words of the notification, per language of the app's interface."""

REASONS = {
    "vi": {
        "slotFull": "Hết chỗ",
        "courtFull": "Sân {court} đã kín",
        "refused": "App từ chối: {message}",
        "unknown": "Không rõ đã đặt được chưa, xem app Vinhomes",
        "notOpen": "Ngày chưa mở đặt",
        "stuck": "App không chuyển màn hình",
        "busy": "Đang có lần chạy khác",
        "loggedOut": "App Vinhomes chưa mở được, có thể đã bị đăng xuất",
        "other": "Có lỗi, xem nhật ký",
    },
    "en": {
        "slotFull": "Fully booked",
        "courtFull": "Court {court} fully booked",
        "refused": "The app refused: {message}",
        "unknown": "Outcome unknown, check the Vinhomes app",
        "notOpen": "Not open for booking yet",
        "stuck": "The app did not move on",
        "busy": "Another run was in progress",
        "loggedOut": "The Vinhomes app did not open; it may be logged out",
        "other": "Error, see the activity log",
    },
}
"""Few words for a failure, the same as ``reasons.*`` of the app (``ui/src/i18n/locales``)."""

_PATTERNS = [
    (re.compile(r"^Slot .+ is fully booked$"), "slotFull"),
    (re.compile(r"^Court (?P<court>.+) is fully booked$"), "courtFull"),
    (re.compile(r"^The app refused the booking: (?P<message>.*)$", re.DOTALL), "refused"),
    (re.compile(r"^Outcome unknown:"), "unknown"),
    (re.compile(r" not open after \d+ attempt"), "notOpen"),
    (re.compile(r" but the next screen did not appear$"), "stuck"),
    (re.compile(r"^Another run is in progress"), "busy"),
    (re.compile(r"check that it is logged in$"), "loggedOut"),
]
"""The engine's reasons as it writes them, as in ``ui/src/reasons.ts``."""

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def format_summary(
    results: Sequence[RoundResult], error: str | None = None, dry_run: bool = False
) -> str:
    """Return a short plain-text summary of the run."""
    booked = sum(result.ok for result in results)
    title = f"court-booker: {booked}/{len(results)} ok"
    if dry_run:
        title += " (dry run)"
    lines = [title]
    for result in results:
        lines.append(f"{'OK' if result.ok else 'FAIL'} {result.slot}: {result.detail}")
    if error:
        lines.append(f"Error: {error}")
    return "\n".join(lines)


def http_post(url: str, data: bytes) -> None:
    """POST form data to ``url``."""
    with urllib.request.urlopen(url, data=data, timeout=_TIMEOUT) as response:
        response.read()


def send_telegram(token: str, chat_id: str, text: str, post: Post = http_post) -> bool:
    """Send ``text`` to ``chat_id``; log and return ``False`` on failure, never raise."""
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        post(_API_URL.format(token=token), data)
    except (OSError, ValueError) as exc:  # URLError and HTTPError are OSErrors
        # The URL holds the bot token, so only the error itself is logged.
        logger.warning("Telegram message not sent: %s", exc)
        return False
    logger.info("Telegram summary sent")
    return True


def court_name(court: str) -> str:
    """Return the short name of a court, "S6" for "S6 - Sân tennis", as the app shows it."""
    name = court.split(" - ", 1)[0].strip()
    return name or court


def failure_reason(detail: str | None, language: str = DEFAULT_LANGUAGE) -> str:
    """Return a few words for an engine reason; an unknown one points to the activity log."""
    reasons = REASONS.get(language, REASONS[DEFAULT_LANGUAGE])
    for pattern, key in _PATTERNS:
        match = None if detail is None else pattern.search(detail)
        if match is not None:
            found = match.groupdict()
            if "court" in found:
                found["court"] = court_name(found["court"])
            return reasons[key].format(**found)
    return reasons["other"]


def format_notification(
    results: Sequence[RoundResult],
    error: str | None,
    *,
    dry_run: bool,
    interrupted: bool,
    target: date,
    court: str,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[str, str]:
    """Return the title and the text of the notification for a finished run.

    The text has one line per round: the slot and the court, or why it failed. A run
    that failed before its rounds has one line for its error instead.
    """
    if language not in TEXTS:  # the config is not validated when loaded
        language = DEFAULT_LANGUAGE
    texts = TEXTS[language]
    if interrupted:
        outcome = texts["stopped"]
    elif results:
        booked = sum(result.ok for result in results)
        outcome = texts["booked"].format(booked=booked, total=len(results))
    else:
        outcome = texts["not_booked"]
    day = (
        f"{target.day}/{target.month}"
        if language == DEFAULT_LANGUAGE
        else f"{target.day} {_MONTHS[target.month - 1]}"
    )
    title = texts["title"].format(day=day, outcome=outcome)
    if dry_run:
        title += texts["dry_run"]
    lines = [
        f"✅ {result.slot} · {court_name(court)}"
        if result.ok
        else f"❌ {result.slot} · {failure_reason(result.detail, language)}"
        for result in results
    ]
    if not results and not interrupted:
        lines.append(failure_reason(error, language))
    return title, "\n".join(lines)


def send_windows(title: str, body: str, run: Run | None = None) -> bool:
    """Show a Windows notification; log and return ``False`` on failure, never raise.

    A no-op outside Windows. PowerShell shows it through the WinRT toast API, with the
    script passed encoded so Vietnamese text survives the console's code page.
    """
    if run is None:
        if sys.platform != "win32":
            logger.debug("Windows notification skipped: not on Windows")
            return False
        run = subprocess.run
    script = _SCRIPT.format(app_id=APP_ID, app_name=APP_NAME, xml=_toast_xml(title, body))
    command = [
        _powershell(),
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        base64.b64encode(script.encode("utf-16-le")).decode("ascii"),
    ]
    try:
        completed = run(
            command, capture_output=True, timeout=_WINDOWS_TIMEOUT, creationflags=_NO_WINDOW
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Windows notification not shown: %s", exc)
        return False
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        logger.warning(
            "Windows notification not shown (exit code %d): %s",
            completed.returncode,
            stderr[:_STDERR_LOGGED],
        )
        return False
    logger.info("Windows notification shown")
    return True


def _toast_xml(title: str, body: str) -> str:
    """Return the toast XML with ``title`` and ``body``, apostrophes escaped too."""
    entities = {"'": "&apos;", '"': "&quot;"}
    return (
        "<toast><visual><binding template='ToastGeneric'>"
        f"<text>{escape(title, entities)}</text><text>{escape(body, entities)}</text>"
        "</binding></visual></toast>"
    )


def _powershell() -> str:
    """Return Windows PowerShell's full path, so no other powershell.exe on PATH runs."""
    root = os.environ.get("SYSTEMROOT", "C:\\Windows")
    return os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
