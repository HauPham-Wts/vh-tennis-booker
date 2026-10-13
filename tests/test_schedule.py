"""Scheduled-task tests with a fake schtasks; Task Scheduler is never touched."""

import subprocess
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

import pytest

from court_booker import schedule
from court_booker.errors import ScheduleError

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
PYTHON = Path("C:/Python/pythonw.exe")
CONFIG = Path("D:/VH-Booker/vh-tennis-booker/config.toml")


def build(**overrides):
    kwargs = {
        "wake_at": "05:45",
        "python": PYTHON,
        "config_path": CONFIG,
        "user": r"PC\Hau",
        "today": date(2026, 10, 8),
    }
    kwargs.update(overrides)
    xml = schedule.build_task_xml(**kwargs)
    # ElementTree rejects an encoding declaration on a str; drop the first line.
    return ET.fromstring(xml.split("\n", 1)[1])


def text(root, path):
    return root.find(path, NS).text


def test_task_runs_daily_at_wake_time_and_wakes_the_pc():
    root = build()
    assert text(root, "t:Triggers/t:CalendarTrigger/t:StartBoundary") == "2026-10-08T05:45:00"
    assert text(root, ".//t:DaysInterval") == "1"
    assert text(root, "t:Settings/t:WakeToRun") == "true"
    assert text(root, "t:Settings/t:DisallowStartIfOnBatteries") == "false"
    assert text(root, ".//t:LogonType") == "InteractiveToken"
    assert text(root, ".//t:UserId") == r"PC\Hau"


def test_task_runs_scheduled_booking_with_absolute_config():
    root = build()
    assert Path(text(root, ".//t:Exec/t:Command")) == PYTHON
    arguments = text(root, ".//t:Exec/t:Arguments")
    assert arguments == f'-m court_booker --config "{CONFIG}" --scheduled'
    assert Path(text(root, ".//t:Exec/t:WorkingDirectory")) == CONFIG.parent


def test_special_characters_are_escaped():
    root = build(user=r"R&D\Hau")
    assert text(root, ".//t:UserId") == r"R&D\Hau"


def test_install_passes_utf16_xml_to_schtasks():
    calls = []

    def run(argv):
        xml_path = Path(argv[argv.index("/XML") + 1])
        calls.append((argv, xml_path.read_text(encoding="utf-16")))
        return subprocess.CompletedProcess(argv, 0, stdout="SUCCESS", stderr="")

    schedule.install(CONFIG, "05:45", run=run, python=PYTHON, user=r"PC\Hau")

    argv, xml = calls[0]
    assert argv[:4] == ["schtasks", "/Create", "/TN", "court-booker"]
    assert argv[-1] == "/F"
    assert "<WakeToRun>true</WakeToRun>" in xml


def test_schtasks_failure_raises():
    def run(argv):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="ERROR: Access is denied.")

    with pytest.raises(ScheduleError, match="Access is denied"):
        schedule.remove(run=run)


def test_install_rejects_wake_after_start(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('start_at = "06:00"\n', encoding="utf-8")
    monkeypatch.setattr(schedule, "install", lambda *a, **k: pytest.fail("must not install"))
    assert schedule.main(["install", "--config", str(config), "--wake", "06:30"]) == 1


def test_cli_dispatches_schedule(monkeypatch):
    import court_booker.cli as cli

    seen = []
    monkeypatch.setattr(cli.schedule, "main", lambda argv: seen.append(argv) or 0)
    assert cli.main(["schedule", "status"]) == 0
    assert seen == [["status"]]


@pytest.mark.parametrize(("returncode", "expected"), [(0, True), (1, False)])
def test_installed_asks_schtasks(returncode, expected):
    calls = []

    def run(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout="", stderr="")

    assert schedule.installed(run) is expected
    assert calls == [["schtasks", "/Query", "/TN", "court-booker"]]


def test_installed_without_schtasks_raises():
    def run(argv):
        raise FileNotFoundError("schtasks")

    with pytest.raises(ScheduleError, match="could not run"):
        schedule.installed(run)


def test_the_next_start_is_today_until_it_passes():
    assert schedule.next_start(datetime(2026, 10, 13, 5, 59), "06:00") == datetime(
        2026, 10, 13, 6, 0
    )
    assert schedule.next_start(datetime(2026, 10, 13, 6, 0), "06:00") == datetime(
        2026, 10, 14, 6, 0
    )
    assert schedule.next_start(datetime(2026, 10, 31, 18, 0), "06:00") == datetime(
        2026, 11, 1, 6, 0
    )
