"""Command-line entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from court_booker import __version__, schedule
from court_booker.clock import ntp_offset, resolve_start
from court_booker.config import Config, load_config
from court_booker.errors import AppNotReadyError, CourtBookerError, DeviceError, RequestError
from court_booker.events import EventKind, LogSink, Reporter
from court_booker.logging_setup import LOGGER_NAME, add_file_handler, configure_logging
from court_booker.notify import format_summary, send_telegram
from court_booker.power import keep_awake
from court_booker.runner import RoundResult, connect_device, run_booking

logger = logging.getLogger(LOGGER_NAME)

EXIT_OK = 0
EXIT_ROUND_FAILED = 1
EXIT_BAD_REQUEST = 2
EXIT_DEVICE = 3
EXIT_APP_NOT_READY = 4
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
    parser.add_argument("--days", type=int, help="days ahead of today to book")
    parser.add_argument("--slots", nargs="+", metavar="SLOT", help='e.g. "18:00 - 19:00"')
    parser.add_argument("--device", help='ADB serial, e.g. 127.0.0.1:16384, or "auto"')
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument(
        "--at", metavar="HH:MM[:SS]", help="prepare now, start booking at this time today"
    )
    timing.add_argument(
        "--scheduled", action="store_true", help="like --at, using start_at from the config"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def apply_overrides(config: Config, args: argparse.Namespace) -> Config:
    if args.days is not None:
        config.days_ahead = args.days
    if args.slots:
        config.slots = args.slots
    if args.device:
        config.device = args.device
    return config


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
    return EXIT_ROUND_FAILED


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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["schedule"]:
        return schedule.main(argv[1:])
    args = build_parser().parse_args(argv)
    configure_logging(verbose=args.verbose)
    report = Reporter(LogSink())
    started = False
    results: list[RoundResult] = []
    config: Config | None = None
    error: str | None = None
    try:
        config = apply_overrides(load_config(args.config), args)
        if config.log_dir:
            # Relative to the config file, since a scheduled task may start elsewhere.
            log_dir = Path(args.config).resolve().parent / config.log_dir
            logger.debug("Logging to %s", add_file_handler(log_dir))
        logger.info("court-booker %s", __version__)
        # Shows whether the scheduled task ran the runner folder or a development checkout.
        logger.debug("Python %s, code in %s", sys.executable, Path(__file__).resolve().parent)
        start_text = config.start_at if args.scheduled else args.at
        start = resolve_start(start_text, datetime.now()) if start_text else None
        report(
            EventKind.RUN_STARTED,
            trigger=run_trigger(args),
            dry_run=args.dry_run,
            slots=list(config.slots),
            start=None if start is None else start.isoformat(timespec="seconds"),
            version=__version__,
        )
        started = True
        with keep_awake():
            offset = 0.0
            if start is not None and config.ntp_server:
                offset = ntp_offset(config.ntp_server) or 0.0
                logger.info("Clock offset %+.3f s", offset)
            device = connect_device(config)
            report(EventKind.DEVICE_READY)
            run_booking(
                device,
                config,
                dry_run=args.dry_run,
                start=start,
                offset=offset,
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
    except Exception as exc:  # an unattended run must still log and report
        logger.exception("Unexpected error")
        error, code = repr(exc), EXIT_ROUND_FAILED

    print_summary(results)
    if started:
        report(
            EventKind.RUN_FINISHED,
            status=run_status(results, error, code == EXIT_INTERRUPTED),
            booked=sum(result.ok for result in results),
            total=len(results),
            error=error,
        )
    if config is not None and config.telegram_token and config.telegram_chat_id:
        text = format_summary(results, error, dry_run=args.dry_run)
        send_telegram(config.telegram_token, config.telegram_chat_id, text)
    return code
