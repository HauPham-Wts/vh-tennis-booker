"""Command-line entry point."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, NoReturn

from court_booker import __version__, device_setup, schedule
from court_booker.adb import AUTO
from court_booker.clock import NtpClock, ntp_offset, resolve_start
from court_booker.config import DAYS_AHEAD, Config, instance_config, load_config
from court_booker.device_setup import Check, Status, Tools, find_tools, run_checks
from court_booker.emulator import MuMu
from court_booker.errors import (
    AppNotReadyError,
    CourtBookerError,
    DeviceError,
    DeviceNotRespondingError,
    EmulatorError,
    LockHeldError,
    RequestError,
)
from court_booker.events import EventKind, LogSink, MultiSink, Reporter
from court_booker.history import History, close_history, open_history
from court_booker.lock import TAKE_OVER_AHEAD, RunLock, check_quiet_time
from court_booker.logging_setup import LOGGER_NAME, add_file_handler, configure_logging
from court_booker.notify import format_notification, format_summary, send_telegram, send_windows
from court_booker.paths import data_folder
from court_booker.power import keep_awake
from court_booker.runner import AUTO_DRIVER, DRIVERS, RoundResult, connect_device, run_booking

logger = logging.getLogger(LOGGER_NAME)

EXIT_OK = 0
EXIT_ROUND_FAILED = 1
EXIT_BAD_REQUEST = 2
EXIT_DEVICE = 3
EXIT_APP_NOT_READY = 4
EXIT_BUSY = 5
EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="court-booker",
        description="Book tennis-court slots in the Vinhomes Resident app via UI automation.",
    )
    parser.add_argument(
        "--config", default="config.toml", help="config file (default: %(default)s)"
    )
    parser.add_argument("--dry-run", action="store_true", help="stop before the final confirmation")
    parser.add_argument("--slots", nargs="+", metavar="SLOT", help='e.g. "18:00 - 19:00"')
    parser.add_argument("--device", help='ADB serial, e.g. 127.0.0.1:16384, or "auto"')
    parser.add_argument(
        "--driver",
        choices=DRIVERS,
        default=AUTO_DRIVER,
        help="drive the device with the instrumentation driver, else uiautomator2 if it does "
        "not start (default: %(default)s), or with one of them only",
    )
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument(
        "--at", metavar="HH:MM[:SS]", help="prepare now, start booking at this time today"
    )
    timing.add_argument(
        "--scheduled", action="store_true", help="like --at, using start_at from the config"
    )
    parser.add_argument(
        "--instance",
        type=int,
        metavar="N",
        help="book with the [[instances]] entry of MuMu instance N only; a run starts one "
        "such process for each entry",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def apply_overrides(config: Config, args: argparse.Namespace) -> Config:
    if args.slots:
        config.slots = args.slots
    if args.device:
        config.device = args.device
    return config


def select_instance(config: Config, index: int) -> Config:
    """Return the settings of the ``[[instances]]`` entry of MuMu instance ``index``."""
    for table in config.instances:
        if table.get("mumu_index") == index:
            return instance_config(config, table)
    raise RequestError(f"The config has no [[instances]] entry with mumu_index = {index}")


def instance_argv(args: argparse.Namespace, index: int) -> list[str]:
    """Return the arguments of the process that books with MuMu instance ``index``.

    That process books with the instance's own settings, so ``--slots`` and ``--device``
    stay with this one.
    """
    argv = ["--config", str(Path(args.config).resolve()), "--instance", str(index)]
    argv += ["--driver", args.driver]
    if args.dry_run:
        argv.append("--dry-run")
    if args.at:
        argv += ["--at", args.at]
    if args.scheduled:
        argv.append("--scheduled")
    if args.verbose:
        argv.append("--verbose")
    return argv


def start_instances(
    args: argparse.Namespace, config: Config
) -> list[tuple[int, subprocess.Popen[bytes]]]:
    """Start a process for each ``[[instances]]`` entry and return them with their index.

    Each books like this process, with its own account and settings, run lock, log file,
    history entry and notification, so an instance that fails or freezes holds up no other.
    Its console output is dropped: its log file has it all.
    """
    if not config.instances:
        return []
    if not config.mumu_manager or config.device != AUTO:
        logger.warning(
            'Other MuMu instances need mumu_manager and device = "auto"; booking with '
            "instance %d alone",
            config.mumu_index,
        )
        return []
    started = []
    taken = {config.mumu_index}
    for table in config.instances:
        index = table.get("mumu_index")
        if not isinstance(index, int) or index in taken:
            logger.warning("Skipping the [[instances]] entry with mumu_index = %r", index)
            continue
        taken.add(index)
        command = [sys.executable, "-m", "court_booker", *instance_argv(args, index)]
        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL)
        except OSError as exc:
            logger.warning("Could not start MuMu instance %d's process: %s", index, exc)
            continue
        logger.info("MuMu instance %d books in process %d", index, process.pid)
        started.append((index, process))
    return started


def wait_for_instances(processes: list[tuple[int, subprocess.Popen[bytes]]]) -> None:
    """Wait for the other instances' processes, so a scheduled task ends after them too."""
    for index, process in processes:
        try:
            code = process.wait()
        except KeyboardInterrupt:  # the Ctrl+C reached them as well
            return
        logger.info("MuMu instance %d finished with exit code %d", index, code)


def print_summary(results: list[RoundResult]) -> None:
    """Log one line per finished round."""
    if not results:
        return
    logger.info("Summary")
    for result in results:
        status = "OK  " if result.ok else "FAIL"
        logger.info("  %s %s  %s  (%.1fs)", status, result.slot, result.detail, result.seconds)


def exit_code(error: CourtBookerError) -> int:
    """Map a run-level error to the process exit code."""
    if isinstance(error, RequestError):
        return EXIT_BAD_REQUEST
    if isinstance(error, DeviceError):
        return EXIT_DEVICE
    if isinstance(error, AppNotReadyError):
        return EXIT_APP_NOT_READY
    if isinstance(error, LockHeldError):
        return EXIT_BUSY
    return EXIT_ROUND_FAILED


def end_process(code: int) -> NoReturn:
    """Exit at once with ``code``, skipping the exit hooks.

    After the emulator froze, a thread may still wait on it, and the exit hook of
    uiautomator2 can wait for that thread: a normal exit could hang until Task Scheduler
    ends the task an hour later.
    """
    logging.shutdown()
    for stream in (sys.stdout, sys.stderr):  # None under pythonw
        if stream is not None:
            stream.flush()
    os._exit(code)


def close_emulator(config: Config) -> None:
    """Shut the MuMu instance down; a failure only logs a warning, as the run is over."""
    logger.info("Closing MuMu instance %d", config.mumu_index)
    try:
        MuMu(Path(config.mumu_manager), config.mumu_index).shutdown()
    except EmulatorError as exc:
        logger.warning("Could not close MuMu: %s", exc)


def close_device(device: Any) -> None:
    """Stop the driver after the run, so uiautomator2 and other tools can use the device."""
    try:
        device.close()
    except Exception:  # the rounds are over: a failure here only goes to the log
        logger.warning("Could not stop the driver", exc_info=True)


def run_trigger(args: argparse.Namespace) -> str:
    """Return what started the run: ``scheduled``, ``dry_run`` or ``manual``."""
    if args.scheduled:
        return "scheduled"
    return "dry_run" if args.dry_run else "manual"


def run_status(results: list[RoundResult], error: str | None, interrupted: bool) -> str:
    """Return ``ok``, ``partial``, ``failed`` or ``interrupted`` for a finished run."""
    if interrupted:
        return "interrupted"
    booked = sum(result.ok for result in results)
    if results and booked == len(results) and error is None:
        return "ok"
    return "partial" if booked else "failed"


def notify_windows(
    config: Config,
    results: list[RoundResult],
    error: str | None,
    *,
    dry_run: bool,
    interrupted: bool,
    target: date,
    instance: int | None = None,
) -> None:
    """Show the outcome as a Windows notification if it is on; a failure only logs."""
    if not config.windows_notification:
        return
    try:
        title, body = format_notification(
            results,
            error,
            dry_run=dry_run,
            interrupted=interrupted,
            target=target,
            court=config.court,
            language=config.notification_language,
            instance=instance,
        )
        send_windows(title, body)
    except Exception:  # reporting never costs a booking
        logger.warning("Windows notification not shown", exc_info=True)


def setup_main(argv: list[str]) -> int:
    """Run ``court-booker setup``: check the PC and MuMu; ``--auto`` fixes what it can."""
    parser = argparse.ArgumentParser(
        prog="court-booker setup",
        description="Check the PC and the emulator for booking; --auto fixes what it can.",
    )
    parser.add_argument(
        "--config", default="config.toml", help="config file (default: %(default)s)"
    )
    parser.add_argument("--auto", action="store_true", help="fix every item that can be fixed")
    parser.add_argument(
        "--restart-mumu",
        action="store_true",
        help="with --auto, restart a running MuMu to apply its new screen",
    )
    args = parser.parse_args(argv)
    configure_logging()
    try:
        config = load_config(args.config)
        tools = find_tools(config)
        results = run_auto_setup(args, config, tools) if args.auto else run_checks(config, tools)
    except CourtBookerError as exc:
        logger.error("%s", exc)
        return exit_code(exc)
    for result in results:
        print(f"{result.status.value:8} {result.item:15} {result.detail}")
    done = all(result.status in (Status.OK, Status.FIXED) for result in results)
    return EXIT_OK if done else EXIT_ROUND_FAILED


def run_auto_setup(args: argparse.Namespace, config: Config, tools: Tools) -> list[Check]:
    """Run auto setup with its log file and its history, like a run."""
    now = datetime.now()
    check_quiet_time(now, config.wake_at, config.start_at, "auto setup")
    if config.log_dir:
        logger.debug(
            "Logging to %s", add_file_handler(Path(args.config).resolve().parent / config.log_dir)
        )
    folder = data_folder()
    history = open_history(folder.database)
    report = Reporter(LogSink() if history is None else MultiSink(LogSink(), history))
    try:
        return device_setup.run_auto_setup(
            config,
            Path(args.config),
            tools,
            folder.lock,
            report,
            restart_mumu=args.restart_mumu,
            now=now,
        )
    finally:
        if history is not None:
            close_history(history)


def serve(argv: list[str]) -> int:
    """Run ``court-booker serve``; the backend is imported only here, runs do not need it."""
    try:
        from court_booker.api.server import main as serve_main
    except ModuleNotFoundError as exc:
        configure_logging()
        logger.error('The backend needs the app extra (pip install -e ".[app]"): %s', exc)
        return EXIT_BAD_REQUEST
    return serve_main(argv)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["schedule"]:
        return schedule.main(argv[1:])
    if argv[:1] == ["setup"]:
        return setup_main(argv[1:])
    if argv[:1] == ["serve"]:
        return serve(argv[1:])
    args = build_parser().parse_args(argv)
    configure_logging(verbose=args.verbose)
    trigger = run_trigger(args)
    report = Reporter(LogSink())
    history: History | None = None
    lock: RunLock | None = None
    started = False
    results: list[RoundResult] = []
    config: Config | None = None
    device: Any = None
    error: str | None = None
    frozen = False
    start: datetime | None = None
    instances: list[tuple[int, subprocess.Popen[bytes]]] = []
    try:
        config = apply_overrides(load_config(args.config), args)
        if args.instance is not None:
            config = select_instance(config, args.instance)
        if config.log_dir:
            # Relative to the config file, since a scheduled task may start elsewhere.
            log_dir = Path(args.config).resolve().parent / config.log_dir
            suffix = "" if args.instance is None else f"-mumu{args.instance}"
            logger.debug("Logging to %s", add_file_handler(log_dir, suffix=suffix))
        # Opened after the log file, so a database that cannot be opened is in the log.
        history = open_history(data_folder().database)
        if history is not None:
            report = Reporter(MultiSink(LogSink(), history))
        logger.info("court-booker %s", __version__)
        # Shows whether the scheduled task ran the runner folder or a development checkout.
        logger.debug("Python %s, code in %s", sys.executable, Path(__file__).resolve().parent)
        now = datetime.now()
        if trigger == "dry_run":
            check_quiet_time(now, config.wake_at, config.start_at, "dry run")
        start_text = config.start_at if args.scheduled else args.at
        start = resolve_start(start_text, now) if start_text else None
        report(
            EventKind.RUN_STARTED,
            trigger=trigger,
            dry_run=args.dry_run,
            slots=list(config.slots),
            start=None if start is None else start.isoformat(timespec="seconds"),
            version=__version__,
            device=config.mumu_index,
        )
        started = True
        folder = data_folder()
        lock = RunLock(
            folder.lock if args.instance is None else folder.instance_lock(args.instance), report
        )
        with keep_awake():
            # Inside keep_awake: a PC woken for the scheduled run must not sleep while it waits.
            if args.scheduled and start is not None:
                lock.acquire_for_schedule(trigger, start - TAKE_OVER_AHEAD)
            else:
                lock.acquire(trigger)
            if args.instance is None:
                if history is not None and lock.held is not None:
                    history.interrupt_stale_runs()
                # Only now: the cleanup above would take the instances' runs for stale ones.
                instances = start_instances(args, config)
            clock = NtpClock(config.ntp_server, ntp_offset)
            if start is not None:
                clock.measure()
            device = connect_device(config, args.driver)
            logger.info("Driving the device with %s", device.driver)
            report(EventKind.DEVICE_READY, driver=device.driver)
            run_booking(
                device,
                config,
                dry_run=args.dry_run,
                start=start,
                clock=clock,
                results=results,
                report=report,
            )
        code = EXIT_OK if all(result.ok for result in results) else EXIT_ROUND_FAILED
    except KeyboardInterrupt:
        logger.warning("Interrupted")
        error, code = "interrupted", EXIT_INTERRUPTED
    except CourtBookerError as exc:
        logger.error("%s", exc)
        error, code = str(exc), exit_code(exc)
        frozen = isinstance(exc, DeviceNotRespondingError)
    except Exception as exc:  # an unattended run must still log and report
        logger.exception("Unexpected error")
        error, code = repr(exc), EXIT_ROUND_FAILED

    if device is not None and not frozen:
        close_device(device)
    print_summary(results)
    if started:
        report(
            EventKind.RUN_FINISHED,
            status=run_status(results, error, code == EXIT_INTERRUPTED),
            booked=sum(result.ok for result in results),
            total=len(results),
            error=error,
        )
    # Each instance of a run with several reports on its own, under its number.
    shown = config or Config()  # also after a config that did not load: the defaults
    instance = shown.mumu_index if args.instance is not None or instances else None
    if config is not None and config.telegram_token and config.telegram_chat_id:
        text = format_summary(results, error, dry_run=args.dry_run, instance=instance)
        send_telegram(config.telegram_token, config.telegram_chat_id, text)
    notify_windows(
        shown,
        results,
        error,
        dry_run=args.dry_run,
        interrupted=code == EXIT_INTERRUPTED,
        target=(start or datetime.now()).date() + timedelta(days=DAYS_AHEAD),
        instance=instance,
    )
    # A real run closes MuMu once its rounds ran; the next run starts it again. MuMu stays
    # open after a dry run, Ctrl+C or an error before the rounds, for whoever is at the PC,
    # and when frozen, since MuMuManager does not shut a frozen instance down.
    if (
        config is not None
        and config.mumu_manager
        and not args.dry_run
        and results
        and code != EXIT_INTERRUPTED
        and not frozen
    ):
        close_emulator(config)
    if not frozen:
        # Holding the lock meanwhile: the run, with its instances, is still going on.
        wait_for_instances(instances)
    if lock is not None:
        lock.release()
    if history is not None:
        close_history(history)
    if frozen:
        end_process(code)
    return code
