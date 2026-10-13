"""Register the daily Windows scheduled task that wakes the PC and runs a booking."""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from court_booker.clock import parse_time
from court_booker.config import load_config
from court_booker.emulator import Run, run_command
from court_booker.errors import CourtBookerError, RequestError, ScheduleError
from court_booker.logging_setup import LOGGER_NAME, configure_logging

logger = logging.getLogger(LOGGER_NAME)

TASK_NAME = "court-booker"

_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Wake the PC and book tennis courts when bookings open.</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>false</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
      <WorkingDirectory>{workdir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def windowless_python(executable: Path) -> Path:
    """Return ``pythonw.exe`` next to ``executable`` if present, so no console opens."""
    candidate = executable.with_name("pythonw.exe")
    return candidate if candidate.is_file() else executable


def current_user() -> str:
    """Return ``DOMAIN\\user`` for the task principal."""
    domain = os.environ.get("USERDOMAIN")
    user = getpass.getuser()
    return f"{domain}\\{user}" if domain else user


def build_task_xml(
    *,
    wake_at: str,
    python: Path,
    config_path: Path,
    user: str,
    today: date,
) -> str:
    """Return Task Scheduler XML running ``--scheduled`` daily at ``wake_at``.

    The task wakes the PC from sleep and runs only while ``user`` is signed in,
    because the emulator needs the interactive desktop.
    """
    wake = parse_time(wake_at, "wake_at")
    arguments = f'-m court_booker --config "{config_path}" --scheduled'
    return _TASK_XML.format(
        start_boundary=datetime.combine(today, wake).isoformat(timespec="seconds"),
        user=escape(user),
        command=escape(str(python)),
        arguments=escape(arguments),
        workdir=escape(str(config_path.parent)),
    )


def install(
    config_path: Path,
    wake_at: str,
    run: Run = run_command,
    python: Path | None = None,
    user: str | None = None,
    today: date | None = None,
) -> None:
    """Create or replace the scheduled task."""
    xml = build_task_xml(
        wake_at=wake_at,
        python=python or windowless_python(Path(sys.executable)),
        config_path=config_path,
        user=user or current_user(),
        today=today or date.today(),
    )
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "task.xml"
        path.write_text(xml, encoding="utf-16")
        _schtasks(run, "/Create", "/TN", TASK_NAME, "/XML", str(path), "/F")


def remove(run: Run = run_command) -> None:
    """Delete the scheduled task."""
    _schtasks(run, "/Delete", "/TN", TASK_NAME, "/F")


def installed(run: Run = run_command) -> bool:
    """Return whether the daily task exists."""
    try:
        result = run(["schtasks", "/Query", "/TN", TASK_NAME])
    except OSError as exc:
        raise ScheduleError(f"schtasks could not run: {exc}") from exc
    return result.returncode == 0


def status(run: Run = run_command) -> str:
    """Return the scheduled task details as printed by ``schtasks``."""
    return _schtasks(run, "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST")


def main(argv: list[str]) -> int:
    """Run ``court-booker schedule install|remove|status``."""
    parser = argparse.ArgumentParser(
        prog="court-booker schedule",
        description="Manage the daily Windows scheduled task.",
    )
    parser.add_argument("action", choices=["install", "remove", "status"])
    parser.add_argument(
        "--config", default="config.toml", help="config file (default: %(default)s)"
    )
    parser.add_argument("--wake", metavar="HH:MM", help="task time; default wake_at in config")
    args = parser.parse_args(argv)
    configure_logging()

    try:
        if args.action == "install":
            config_path = Path(args.config).resolve()
            if not config_path.is_file():
                raise RequestError(f"{config_path} not found; create it from config.example.toml")
            config = load_config(config_path)
            wake_at = args.wake or config.wake_at
            if parse_time(wake_at, "wake_at") >= parse_time(config.start_at, "start_at"):
                raise RequestError(f"wake_at {wake_at} must be before start_at {config.start_at}")
            install(config_path, wake_at)
            logger.info(
                "Task %r runs daily at %s and books at %s", TASK_NAME, wake_at, config.start_at
            )
        elif args.action == "remove":
            remove()
            logger.info("Task %r removed", TASK_NAME)
        else:
            print(status())
    except CourtBookerError as exc:
        logger.error("%s", exc)
        return 1
    return 0


def _schtasks(run: Run, *args: str) -> str:
    try:
        result = run(["schtasks", *args])
    except OSError as exc:
        raise ScheduleError(f"schtasks could not run: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ScheduleError(f"schtasks {args[0]} failed: {detail}")
    return result.stdout
