"""One booking run: connect to the device and book every configured slot."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from court_booker.adb import Adb, find_adb, resolve_device
from court_booker.clock import wait_until
from court_booker.config import Config
from court_booker.emulator import MuMu
from court_booker.errors import BookingError, DeviceConnectionError, DeviceNotRespondingError
from court_booker.events import EventKind, Reporter
from court_booker.flow import Booker, log_screen
from court_booker.watchdog import GuardedDevice, Watchdog

logger = logging.getLogger(__name__)

LOCATE_AHEAD = timedelta(seconds=2)
"""How long before the start time the utilities entry is read again."""


@dataclass
class RoundResult:
    """Outcome of one booking round."""

    slot: str
    ok: bool
    detail: str
    seconds: float


def log_last_screen(booker: Booker) -> None:
    """Log every element of the last screen ``booker`` read, to diagnose a failure.

    A failure that happens only at the opening time, or only on the last days of a
    month, can then be fixed from the log of a single run.
    """
    log_screen(booker.last_screen, "Last screen read")


class QuickTap:
    """Pass every call on to ``device``, except taps, sent as a bare touch down and up.

    uiautomator2's ``click`` holds the touch for about 100 ms (Android ``UiDevice.click``):
    151-165 ms a tap on MuMu, against 83-91 ms for a touch down and up, which the app took
    every time (2026-10-16).
    """

    def __init__(self, device: Any) -> None:
        self._device = device

    def click(self, x: int, y: int) -> None:
        """Tap ``(x, y)``; both events in one call, so the watchdog limits the whole tap."""
        self._device.touch.down(x, y).up(x, y)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._device, name)


def connect_device(config: Config) -> Any:
    """Start the emulator if configured and return a uiautomator2 device.

    The connection and every command on the device returned are time-limited
    (:mod:`court_booker.watchdog`), so a frozen emulator ends the run instead of hanging it.
    Taps skip uiautomator2's hold (:class:`QuickTap`).
    """
    import uiautomator2  # deferred so tests do not require the dependency

    preferred = None
    extra_dirs = []
    if config.mumu_manager:
        mumu = MuMu(Path(config.mumu_manager), config.mumu_index)
        mumu.ensure_started(config.boot_timeout)
        preferred = mumu.adb_serial()
        extra_dirs.append(mumu.manager.parent)

    adb = Adb(find_adb(config.adb_path, extra_dirs))
    serial = resolve_device(adb, config.device, preferred)
    logger.info("Connecting to %s", serial)
    watchdog = Watchdog()
    try:
        device = watchdog.run("connect", lambda: uiautomator2.connect(serial))
    except DeviceNotRespondingError:
        raise
    except Exception as exc:  # uiautomator2 raises several unrelated types
        raise DeviceConnectionError(f"Could not connect to {serial}: {exc}") from exc
    return GuardedDevice(QuickTap(device), watchdog)


def run_booking(
    device: Any,
    config: Config,
    *,
    dry_run: bool = False,
    start: datetime | None = None,
    offset: float = 0.0,
    results: list[RoundResult] | None = None,
    report: Reporter | None = None,
) -> list[RoundResult]:
    """Prepare the app, wait for ``start`` if given, then book every configured slot.

    ``offset`` corrects the local clock (see :func:`clock.ntp_offset`). The target
    date is ``days_ahead`` after the start date. Results are appended to
    ``results`` as rounds finish, so an interrupted caller still sees them; progress
    goes to ``report`` as events.
    """
    results = [] if results is None else results
    report = Reporter() if report is None else report
    booker = Booker(device, config, report)
    try:
        booker.prepare()
        report(EventKind.APP_READY)
        if start is not None:
            report(EventKind.WAITING, until=start.isoformat(timespec="seconds"))
            # Wait on the home screen, then load the utilities list shortly before the
            # start, so the app has just talked to its server when the first tap comes.
            wait_until(start - timedelta(seconds=config.warm_up_seconds), offset)
            try:
                booker.locate_entry()
            except BookingError as exc:
                logger.warning("Could not open the utilities list yet (%s); retrying", exc)
            wait_until(start - LOCATE_AHEAD, offset)
            booker.locate_entry()
            wait_until(start, offset)
    except Exception:  # the caller logs the error itself
        log_last_screen(booker)
        raise
    target = (start or datetime.now()).date() + timedelta(days=config.days_ahead)
    logger.info(
        "Target date %s, slots: %s%s",
        target.isoformat(),
        ", ".join(config.slots),
        " (dry run)" if dry_run else "",
    )
    report(
        EventKind.BOOKING_STARTED,
        date=target.isoformat(),
        court=config.court,
        slots=list(config.slots),
        dry_run=dry_run,
    )

    for index, slot in enumerate(config.slots, start=1):
        logger.info("Round %d/%d: %s", index, len(config.slots), slot)
        report(EventKind.SLOT_STARTED, slot=slot, round=index, rounds=len(config.slots))
        started = time.perf_counter()
        commands = booker.commands
        shown: dict[str, Any] = {}
        frozen: DeviceNotRespondingError | None = None
        try:
            shown = booker.book(slot, target, dry_run=dry_run).event_data()
        except DeviceNotRespondingError as exc:
            # A frozen emulator answers no later round either: end the run after this one.
            log_last_screen(booker)
            ok, detail, frozen = False, str(exc), exc
        except BookingError as exc:
            logger.error("%s", exc)
            log_last_screen(booker)
            ok, detail = False, str(exc)
        except Exception as exc:  # keep later rounds running on device glitches
            logger.exception("Unexpected error")
            log_last_screen(booker)
            ok, detail = False, repr(exc)
        else:
            ok, detail = True, "dry run passed" if dry_run else "booked"
        seconds = time.perf_counter() - started
        used = booker.commands - commands
        results.append(RoundResult(slot, ok, detail, seconds))
        logger.debug("Round %d used %d device commands", index, used)
        if ok:
            report(
                EventKind.SLOT_BOOKED,
                slot=slot,
                seconds=round(seconds, 1),
                commands=used,
                dry_run=dry_run,
                **shown,
            )
        else:
            report(
                EventKind.SLOT_FAILED,
                slot=slot,
                reason=detail,
                seconds=round(seconds, 1),
                commands=used,
            )
        if frozen is not None:
            raise frozen
    return results
