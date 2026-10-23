"""Notification tests with a fake HTTP post and PowerShell; no network or toast."""

import base64
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
from datetime import date
from pathlib import Path

import pytest

from court_booker.notify import (
    REASONS,
    failure_reason,
    format_notification,
    format_summary,
    send_telegram,
    send_windows,
)
from court_booker.runner import RoundResult

RESULTS = [
    RoundResult("18:00 - 19:00", True, "booked", 4.2),
    RoundResult("19:00 - 20:00", False, "Slot 19:00 - 20:00 is fully booked", 2.1),
]


def test_format_summary():
    text = format_summary(RESULTS)
    assert text.splitlines() == [
        "court-booker: 1/2 ok",
        "OK 18:00 - 19:00: booked",
        "FAIL 19:00 - 20:00: Slot 19:00 - 20:00 is fully booked",
    ]


def test_format_summary_with_run_error():
    text = format_summary([], error="MuMu did not start", dry_run=True)
    assert text.splitlines() == ["court-booker: 0/0 ok (dry run)", "Error: MuMu did not start"]


def test_send_telegram_posts_chat_and_text():
    sent = []
    assert send_telegram("123:abc", "42", "hello", post=lambda url, data: sent.append((url, data)))
    url, data = sent[0]
    assert url == "https://api.telegram.org/bot123:abc/sendMessage"
    assert urllib.parse.parse_qs(data.decode()) == {"chat_id": ["42"], "text": ["hello"]}


def test_send_telegram_failure_is_logged_not_raised(caplog):
    def post(url, data):
        raise urllib.error.URLError("no network")

    assert send_telegram("123:secret", "42", "hello", post=post) is False
    assert "no network" in caplog.text
    assert "secret" not in caplog.text


TARGET = date(2026, 10, 26)
COURT = "S6 - Sân tennis"


def notification(results, error=None, language="vi", dry_run=False, interrupted=False):
    return format_notification(
        results,
        error,
        dry_run=dry_run,
        interrupted=interrupted,
        target=TARGET,
        court=COURT,
        language=language,
    )


def test_notification_has_a_line_per_round_in_vietnamese():
    title, body = notification(RESULTS)

    assert title == "Đặt sân 26/10: 1/2 thành công"
    assert body.splitlines() == ["✅ 18:00 - 19:00 · S6", "❌ 19:00 - 20:00 · Hết chỗ"]


def test_notification_in_english():
    title, body = notification(RESULTS, language="en")

    assert title == "Courts for 26 Oct: 1/2 booked"
    assert body.splitlines() == ["✅ 18:00 - 19:00 · S6", "❌ 19:00 - 20:00 · Fully booked"]


def test_notification_of_a_dry_run_says_so():
    passed = [RoundResult("18:00 - 19:00", True, "dry run passed", 3.0)]

    assert notification(passed, dry_run=True)[0] == "Đặt sân 26/10: 1/1 thành công (chạy thử)"
    assert notification(passed, dry_run=True, language="en")[0].endswith(": 1/1 booked (dry run)")


def test_a_run_that_failed_before_its_rounds_gives_its_reason():
    error = "Another run is in progress (dry_run, pid 42)"

    assert notification([], error) == ("Đặt sân 26/10: không đặt được", "Đang có lần chạy khác")
    assert notification([], "MuMu did not start", language="en") == (
        "Courts for 26 Oct: not booked",
        "Error, see the activity log",
    )


def test_a_stopped_run_lists_its_finished_rounds():
    title, body = notification(RESULTS[:1], "interrupted", interrupted=True)

    assert title == "Đặt sân 26/10: đã dừng"
    assert body == "✅ 18:00 - 19:00 · S6"
    assert notification([], "interrupted", interrupted=True) == ("Đặt sân 26/10: đã dừng", "")


def test_an_unknown_language_falls_back_to_vietnamese():
    assert notification(RESULTS, language="fr")[0] == "Đặt sân 26/10: 1/2 thành công"


@pytest.mark.parametrize(
    ("detail", "vi", "en"),
    [
        ("Slot 19:00 - 20:00 is fully booked", "Hết chỗ", "Fully booked"),
        ("Court S6 - Sân tennis is fully booked", "Sân S6 đã kín", "Court S6 fully booked"),
        (
            "The app refused the booking: Quá số lần\nđặt",
            "App từ chối: Quá số lần\nđặt",
            "The app refused: Quá số lần\nđặt",
        ),
        (
            "Booking quota used up: Căn hộ đã hết hạn mức đăng ký tiện ích cho phép.",
            "Hết hạn mức đặt sân",
            "Booking quota used up",
        ),
        (
            "Skipped: the booking quota is used up",
            "Bỏ qua vì đã hết hạn mức",
            "Skipped: booking quota used up",
        ),
        (
            "Outcome unknown: no ticket 30 s after confirming",
            "Không rõ đã đặt được chưa, xem app Vinhomes",
            "Outcome unknown, check the Vinhomes app",
        ),
        ("Date 26 not open after 12 attempts", "Ngày chưa mở đặt", "Not open for booking yet"),
        (
            "Tapped 'Tiếp tục' but the next screen did not appear",
            "App không chuyển màn hình",
            "The app did not move on",
        ),
        (
            "The app did not show 'Tiện ích'; check that it is logged in",
            "App Vinhomes chưa mở được, có thể đã bị đăng xuất",
            "The Vinhomes app did not open; it may be logged out",
        ),
        (
            "Button not found: 'S6 - Sân tennis'",
            "Có lỗi, xem nhật ký",
            "Error, see the activity log",
        ),
        (None, "Có lỗi, xem nhật ký", "Error, see the activity log"),
    ],
)
def test_failure_reasons_read_as_in_the_app(detail, vi, en):
    assert failure_reason(detail, "vi") == vi
    assert failure_reason(detail, "en") == en


@pytest.mark.parametrize("language", ["vi", "en"])
def test_reasons_match_the_app_translations(language):
    locale = Path(__file__).resolve().parents[1] / "ui" / "src" / "i18n" / "locales"
    reasons = json.loads((locale / f"{language}.json").read_text(encoding="utf-8"))["reasons"]

    assert {key: re.sub(r"\{\{(\w+)\}\}", r"{\1}", text) for key, text in reasons.items()} == (
        REASONS[language]
    )


def completed(returncode=0, stderr=b""):
    return subprocess.CompletedProcess([], returncode, b"", stderr)


def test_send_windows_runs_an_encoded_powershell_script():
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return completed()

    assert send_windows("Đặt sân 26/10: 1/2 thành công", "✅ a\n❌ <b> & 'c'", run=run)
    (command, kwargs), *_ = calls
    assert Path(command[0]).parts[-4:] == (
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    assert command[1:4] == ["-NoProfile", "-NonInteractive", "-EncodedCommand"]
    script = base64.b64decode(command[4]).decode("utf-16-le")
    assert r"AppUserModelId\CourtBooker'" in script
    assert "-Value 'Court Booker'" in script
    assert "<text>Đặt sân 26/10: 1/2 thành công</text>" in script
    assert "<text>✅ a\n❌ &lt;b&gt; &amp; &apos;c&apos;</text>" in script
    assert "CreateToastNotifier('CourtBooker')" in script
    assert kwargs["capture_output"] is True
    assert kwargs["timeout"] > 0


def test_a_title_cannot_end_the_scripts_here_string():
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return completed()

    send_windows("x\n'@\nRemove-Item C:\\", "", run=run)

    script = base64.b64decode(calls[0][4]).decode("utf-16-le")
    assert "\n'@\n" not in script.split("$xml.LoadXml(@'", 1)[1].split("\n'@)", 1)[0]


@pytest.mark.parametrize(
    "outcome",
    [
        completed(1, b"#< CLIXML\nToast failed"),
        OSError("powershell.exe not found"),
        subprocess.TimeoutExpired("powershell.exe", 20),
    ],
)
def test_a_notification_failure_is_logged_not_raised(outcome, caplog):
    def run(command, **kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    assert send_windows("title", "body", run=run) is False
    assert "Windows notification not shown" in caplog.text


def test_send_windows_does_nothing_outside_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert send_windows("title", "body") is False
