"""One booking run: connect to the device and book every configured slot."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from court_booker.adb import Adb, find_adb, resolve_device
from court_booker.clock import NtpClock, wait_until
from court_booker.config import DAYS_AHEAD, Config
from court_booker.driver import PACKAGE as DRIVER_PACKAGE
from court_booker.driver import connect_driver
from court_booker.emulator import MuMu
from court_booker.errors import (
    BookingError,
    DeviceConnectionError,
    DeviceNotRespondingError,
    QuotaFullError,
)
from court_booker.events import EventKind, Reporter
from court_booker.flow import Booker, log_screen
from court_booker.watchdog import GuardedDevice, Watchdog

logger = logging.getLogger(__name__)

LOCATE_AHEAD = timedelta(seconds=2)
"""How long before the start time the utilities entry is read again."""
OPENING_MARGIN = timedelta(seconds=0.1)
"""How long after the start time a timed run taps first.

The app answered an early tap with a notice on 2026-10-19 (up to 0.76 s early). The
0.1 s margin reduces that risk, but a notice still appeared on 2026-10-20 with the PC
clock behind NTP. Which clock the app uses for opening hours remains unverified.
The 06:00 logs show where the tap fell ("Start reached"); retaps handle a notice."""
QUOTA_SKIPPED = "Skipped: the booking quota is used up"
"""Why a round after the app's quota notice failed without running."""
AUTO_DRIVER = "auto"
INSTRUMENTATION = "instrumentation"
UIAUTOMATOR2 = "uiautomator2"
DRIVERS = (AUTO_DRIVER, INSTRUMENTATION, UIAUTOMATOR2)
"""How the run drives the device: the driver (:mod:`court_booker.driver`) when it starts,
else uiautomator2 (``auto``), or only one of them (for tests by hand)."""


@dataclass
class RoundResult:
    """Outcome of one booking round."""

    slot: str
    ok: bool
    detail: str
    seconds: float
    court: str | None = None
    """The court the confirmation page named, if the round read it: the one booked, which
    once differed from the configured one."""


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

    driver = UIAUTOMATOR2

    def __init__(self, device: Any) -> None:
        self._device = device

    def click(self, x: int, y: int, label: str = "") -> None:
        """Tap ``(x, y)``; both events in one call, so the watchdog limits the whole tap.

        ``label`` is for the driver, which clicks by label; a tap here goes by position only.
        """
        self._device.touch.down(x, y).up(x, y)

    def close(self) -> None:
        """Leave the uiautomator2 server running, as runs always did."""

    def __getattr__(self, name: str) -> Any:
        return getattr(self._device, name)


def connect_device(config: Config, driver: str = AUTO_DRIVER) -> Any:
    """Start the emulator if configured and return the device the run drives.

    That is the driver (:mod:`court_booker.driver`), installed and started as needed, else
    uiautomator2 when the driver does not start, whose taps skip its hold (:class:`QuickTap`);
    ``driver`` can ask for one of them only. The device's ``driver`` attribute names the one
    used, and ``close()`` ends it after the run. The connection and every command on the
    device are time-limited (:mod:`court_booker.watchdog`), so a frozen emulator ends the
    run instead of hanging it.
    """
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
    if driver != UIAUTOMATOR2:
        try:
            device = watchdog.run("connect", lambda: connect_driver(adb, serial))
        except DeviceNotRespondingError:
            raise
        except Exception as exc:  # any driver failure, so it never costs the booking
            if driver == INSTRUMENTATION:
                raise
            logger.warning("Driver unavailable (%s); using uiautomator2", exc)
            # A driver that started and failed after holds UiAutomation, which uiautomator2 needs.
            adb.shell(serial, "am", "force-stop", DRIVER_PACKAGE)
        else:
            return GuardedDevice(device, watchdog)
    return GuardedDevice(QuickTap(connect_uiautomator2(serial, watchdog)), watchdog)


def connect_uiautomator2(serial: str, watchdog: Watchdog) -> Any:
    """Return a uiautomator2 device on ``serial``."""
    import uiautomator2  # deferred so tests do not require the dependency

    try:
        device = watchdog.run("connect", lambda: uiautomator2.connect(serial))
    except DeviceNotRespondingError:
        raise
    except Exception as exc:  # uiautomator2 raises several unrelated types
        raise DeviceConnectionError(f"Could not connect to {serial}: {exc}") from exc
    return device


def run_booking(
    device: Any,
    config: Config,
    *,
    dry_run: bool = False,
    start: datetime | None = None,
    clock: NtpClock | None = None,
    results: list[RoundResult] | None = None,
    report: Reporter | None = None,
) -> list[RoundResult]:
    """Prepare the app, wait for ``start`` if given, then book every configured slot.

    The wait goes by ``clock`` (the PC clock if not given), measured again at the warm-up,
    and ends :data:`OPENING_MARGIN` after ``start``. The target date is
    :data:`~court_booker.config.DAYS_AHEAD` after the start date. After the app's quota
    notice the slots left fail unrun. Results are appended to ``results`` as rounds finish,
    so an interrupted caller still sees them; progress goes to ``report`` as events.
    """
    results = [] if results is None else results
    report = Reporter() if report is None else report
    clock = NtpClock() if clock is None else clock
    booker = Booker(device, config, report)
    try:
        booker.prepare()
        report(EventKind.APP_READY)
        if start is not None:
            report(EventKind.WAITING, until=start.isoformat(timespec="seconds"))
            # Wait on the home screen, then load the utilities list shortly before the
            # start, so the app has just talked to its server when the first tap comes.
            wait_until(start - timedelta(seconds=config.warm_up_seconds), clock.now)
            # A fresh answer leaves the counter only the warm-up to drift, and the log shows
            # how far Windows set the PC clock since the first one.
            clock.measure()
            try:
                booker.locate_entry()
            except BookingError as exc:
                logger.warning("Could not open the utilities list yet (%s); retrying", exc)
            wait_until(start - LOCATE_AHEAD, clock.now)
            booker.locate_entry()
            wait_until(start + OPENING_MARGIN, clock.now)
            logger.info("Start reached at %s", clock.reading())
    except Exception:  # the caller logs the error itself
        log_last_screen(booker)
        raise
    target = (start or datetime.now()).date() + timedelta(days=DAYS_AHEAD)
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
        quota_full = False
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
            quota_full = isinstance(exc, QuotaFullError)
        except Exception as exc:  # keep later rounds running on device glitches
            logger.exception("Unexpected error")
            log_last_screen(booker)
            ok, detail = False, repr(exc)
        else:
            ok, detail = True, "dry run passed" if dry_run else "booked"
        seconds = time.perf_counter() - started
        used = booker.commands - commands
        results.append(RoundResult(slot, ok, detail, seconds, shown.get("shown_court")))
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
        if quota_full:
            skip_rounds(config.slots[index:], results, report)
            break
    return results


def skip_rounds(slots: list[str], results: list[RoundResult], report: Reporter) -> None:
    """Fail ``slots`` without running them: the app's quota notice would refuse each one."""
    if slots:
        logger.warning("Booking quota used up; skipping %s", ", ".join(slots))
    for slot in slots:
        results.append(RoundResult(slot, False, QUOTA_SKIPPED, 0.0))
        report(EventKind.SLOT_FAILED, slot=slot, reason=QUOTA_SKIPPED, seconds=0.0, commands=0)
