"""Booking flow, one method per app screen.

Each screen is read with one hierarchy dump (:class:`~court_booker.screen.Screen`),
which lists every element with its bounds in about the time of a single element
query. Elements are found by accessibility label in that dump, so waiting for the next
screen and locating the next element are the same query: a step costs one dump per poll
plus one tap. A tap names the element by its label: the driver
(:class:`~court_booker.driver.DriverDevice`) clicks the element with that label where it is
then, uiautomator2 (:class:`~court_booker.runner.QuickTap`) taps where the dump showed it.
No coordinates are kept across screens. ``device`` is one of them or a test double with
``dump_hierarchy``, ``click`` (with the label of the element tapped), ``press``, ``swipe``,
``shell`` and the app calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Callable, Optional, TypeVar

from court_booker.app_language import AppLanguage, app_languages
from court_booker.config import Config
from court_booker.errors import (
    AppNotReadyError,
    BookingNotOpenError,
    BookingRejectedError,
    BookingUnconfirmedError,
    ElementNotFoundError,
    NavigationError,
    QuotaFullError,
    SlotUnavailableError,
)
from court_booker.events import EventKind, Reporter
from court_booker.geometry import (
    ANY_SLOT_PATTERN,
    is_checkbox_beside,
    is_inside,
    month_index,
    parse_booked_time,
)
from court_booker.screen import Match, Node, Screen

logger = logging.getLogger(__name__)

T = TypeVar("T")
Finder = Callable[[Screen], Optional[T]]
"""Return what to act on in a screen, or ``None`` while it is not shown yet."""

_POLL_INTERVAL = 0.02
_NEXT_SCREEN_TIMEOUT = 2.0
"""How long a screen may take to show after Back before Back is pressed again."""
_RETAP_AFTER = 2.0
"""How long a tap may go without the next screen before its element, if still shown, is
tapped again: the app swallowed the tap. The calendar stayed 2.3 s after a "Tiếp tục" the
app took (2026-10-11), so a shorter wait would send it twice at 06:00. A tap is never
repeated while the app loads the next screen (the element gone): that waits up to
``timeout``, as the server may be slow."""
_COURT_ATTEMPTS = 5
"""Courts opened by mistake before the round gives up."""
_MOVED_COURT_WAIT = 0.6
"""A court list still shown this long after a court tap, with the court moved, missed it.

A tap that opens a court shows the booking details page 0.23-0.45 s later (14-17/10)."""
_BACK_PRESSES = 8
_CONTINUE_WAIT = 2.0
"""How long the slot list is read again while "Tiếp tục" shows disabled, before the slot tap.

Every booking so far tapped the slot with the button enabled, and 77 reads of the slot list
on 14-18/10 showed both at once; at 06:00:10 on 2026-10-19 the list showed with the button
still disabled. A tap on a page not done yet may be dropped when the page is built again."""
_SLOT_SETTLE = 0.1
"""Pause after the slot tap, before "Tiếp tục": the app takes the slot a few frames later.

A "Tiếp tục" 11-40 ms after the tap booked the slot selected before (3 of 3, with an
accessibility agent, 2026-10-18); 60 and 100 ms got the slot tapped (12 of 12).
uiautomator2's taps were never that close. Nothing on the screen shows the selection, so
there is nothing to wait for."""
_TERMS_SETTLE = 0.2
"""Least time from the checkbox tap to "Xác nhận": the app takes the tick a few frames after
the button shows enabled. A "Xác nhận" 65 ms after the tick did nothing (the driver,
2026-10-18), one 97 ms after it booked, and uiautomator2's 0.14-0.23 s always did."""
_CONFIRM_RETAP_AFTER = 3.0
"""How long "Xác nhận" may go without the ticket or a notice before it is tapped again, if
the confirmation page still shows it enabled: the app swallowed the tap. 2 of 26 rounds under
simulated load (2026-10-19) kept the page unchanged for 30 s with no ticket, and a tap by
hand then booked. The page also stays unchanged while the server answers, so the wait is
about twice the slowest answer at 06:00: the ticket showed 0.66-1.6 s after the tap (7 taps,
15-20/10), 1.1-2.7 s under light lag. A swallowed tap costs 3 s, and a slow answer seldom
gets a second tap."""
_FIRST_DATE_WAIT = 1.5
_NEXT_DATE_WAIT = 0.8
_CHECKBOX_TIMEOUT = 0.8
_SETTLE_TIMEOUT = 1.0
_SWIPE_SECONDS = 0.25
_MIN_VISIBLE_RATIO = 0.6
"""A slot clipped to less than this share of a full slot's height is scrolled into view."""
QUIET_SETTINGS = (
    "window_animation_scale",
    "transition_animation_scale",
    "animator_duration_scale",
    "heads_up_notifications_enabled",
)
"""Android settings set to 0: those Accessibility > Remove animations sets, then the
notification banners that would drop over the top of the app."""


@dataclass
class Booked:
    """What the app showed for a round that went through, for the log and the history.

    Read from screens the round reads anyway, so it costs no device command. A detail not
    found stays ``None``; so do the ticket's in a dry run.
    """

    shown_date: str | None = None
    """ISO date on the confirmation page."""
    shown_slot: str | None = None
    """Slot on the confirmation page."""
    shown_court: str | None = None
    """Court on the confirmation page: the one booked, which once differed from the one tapped."""
    ticket_status: str | None = None
    """The ticket's status in the read that showed the ticket, if it showed already."""

    def event_data(self) -> dict[str, Any]:
        """Return the details found, as data of the ``slot_booked`` event."""
        return {key: value for key, value in asdict(self).items() if value is not None}


class Booker:
    """Drive one booking round per call to :meth:`book`."""

    def __init__(self, device: Any, config: Config, report: Reporter | None = None) -> None:
        self.device = device
        self.config = config
        self.report = Reporter() if report is None else report
        """Receives the steps of each round; reporting sends no device commands."""
        self.commands = 0
        """Device commands sent so far; each is a round trip to the emulator."""
        self.last_screen = Screen([])
        self._entry: Screen | None = None

        self.any_slot = Match(pattern=ANY_SLOT_PATTERN)
        self.court = Match(desc=config.court, clickable=True)
        self.any_court = Match(prefix=config.court, clickable=True)
        self.opened_court = Match(desc=config.court, clickable=False)
        """The court named on the booking details page."""
        self.languages = app_languages(config.labels, config.sport)
        """The languages the app may show; the court names read the same in each."""
        self._use(self.languages[0])

    def _use(self, language: AppLanguage) -> None:
        """Read and tap the app's labels in ``language`` from now on."""
        self.language = language
        self.labels = labels = language.labels
        self.home = Match(desc=labels.home, clickable=True)
        self.utility = Match(desc=labels.utility, clickable=True)
        self.any_day = Match(pattern=language.any_day)
        self.prev_month = Match(desc=labels.prev_month)
        self.next_month = Match(contains=labels.next_month)
        self.continue_button = Match(desc=labels.continue_, clickable=True)
        self.venue_list = Match(desc=labels.venue_list)
        self.court_list = Match(desc=labels.court_list)
        self.residents = Match(contains=labels.residents)
        self.agree = Match(contains=labels.agree)
        self.confirm_button = Match(desc=labels.confirm, clickable=True)
        self.notice = Match(desc=labels.notice)
        self.ticket = Match(desc=labels.ticket)
        self.processing = Match(desc=labels.processing)
        self.registered = Match(desc=labels.registered)

    # Public API -------------------------------------------------------------

    def quiet_device(self) -> None:
        """Turn off Android animations and notification banners in one command.

        Screens then change without transitions, so the next one can be read sooner, and no
        banner can cover the top of the app or add nodes to a dump mid-round. The settings
        stay until changed, and a failure only costs these safeguards.
        """
        command = "; ".join(f"settings put global {name} 0" for name in QUIET_SETTINGS)
        self.commands += 1
        try:
            self.device.shell(command)
        except Exception:  # uiautomator2 raises several unrelated types
            logger.warning("Could not turn off animations and banners", exc_info=True)
            return
        logger.debug("Animations and notification banners off")

    def prepare(self) -> None:
        """Open the app and stop on its home screen, ready for the first round.

        With ``restart_app`` the app is stopped first, so a stale screen, popup or
        expired session from the previous day cannot get in the way. A timed run waits
        on the home screen and opens the utilities list shortly before the start
        (:meth:`locate_entry`), so the list it books from is freshly loaded. The first of
        these screens tells the app's language, whose labels the rounds then use.
        """
        package = self.config.package
        self.quiet_device()
        if self.config.restart_app:
            logger.info("Restarting %s", package)
            self.device.app_stop(package)
            self.device.app_start(package)
        elif self.device.app_current().get("package") != package:
            logger.info("Starting %s", package)
            self.device.app_start(package)

        found = self.wait_for(self._find_language, self.config.boot_timeout)
        if found is None:
            *labels, last = [
                repr(label)
                for language in self.languages
                for label in (language.labels.home, language.labels.utility)
                if label
            ]
            raise AppNotReadyError(
                f"The app did not show {', '.join(labels)} or {last} in "
                f"{self.config.boot_timeout:.0f} s; check that it is logged in"
            )
        if not found[0].labels.utility:
            raise AppNotReadyError(
                f"The app is in {found[0].name}, whose label of {self.config.sport!r} is not "
                "known yet; set the app to Vietnamese"
            )
        self._use(found[0])
        logger.info("App language: %s", found[0].name)
        try:
            self.return_to_home(found[1])
        except NavigationError as exc:
            raise AppNotReadyError(str(exc)) from exc
        logger.info("Ready on the home screen")

    def locate_entry(self) -> None:
        """Open the utilities list from the home screen, or read it again if it is shown.

        A timed run calls this at ``warm_up_seconds`` before the start, which taps
        the home screen's utilities button and loads the list, and again just before
        the start, which only reads it. The first round then taps the utility with a
        single command at the start time.
        """
        self._entry = self.return_to_utilities()
        logger.info("On the utilities list ahead of the start time")

    def book(self, slot: str, target: date, dry_run: bool = False) -> Booked:
        """Book ``slot`` on ``target``, starting from the home or utilities screen.

        Returns what the confirmation page and the ticket showed.
        """
        labels = self.labels
        screen = self.open_slot(slot, target)
        if screen.find(self.continue_button) is None:  # the slot was tapped with it disabled
            found = self.wait_for(self._finder(self.continue_button), self.config.timeout)
            if found is None:
                raise ElementNotFoundError(f"{labels.continue_!r} stayed disabled")
            screen = found[1]
        shown, screen = self.tap_and_advance(
            screen, self.continue_button, labels.continue_, self._after_calendar
        )
        if self.notice(shown):
            raise self._refusal(self.notice_text(screen) or "")
        if not self.court_list(shown) and not self.residents(shown):
            # Only the court list's heading counts after the venue: a read right after the
            # tap may still show the venue (2026-10-23), which ended the round at once.
            venue = Match(desc=shown.desc, clickable=True)
            shown, screen = self.tap_and_advance(screen, venue, shown.desc, self._courts_or_details)
        if not self.residents(shown):
            # A court that the bottom edge cuts off is tapped as it is: it is in the tree, and
            # the driver clicks it by its label (field notes, "Other sports").
            found = self.wait_for(self._court_or_details, self.config.timeout, screen)
            if found is None:
                raise ElementNotFoundError(f"Court {self.config.court!r} is not on the court list")
            shown, screen = found
        if self.residents(shown):
            screen = self.check_single_court(screen)
        else:
            if labels.fully_booked in shown.desc:
                raise SlotUnavailableError(f"Court {self.config.court} is fully booked")
            screen = self.select_court(screen)
        self.report(EventKind.COURT_SELECTED, court=self.config.court)
        point, screen = self.tap_and_advance(
            screen, self.continue_button, labels.continue_, self.locate_checkbox
        )
        booked = self.read_confirmation(screen, slot, target)
        after = self.accept_and_confirm(point, dry_run)
        if after is not None:
            self.read_ticket(after, booked)
        return booked

    def open_slot(self, slot: str, target: date) -> Screen:
        """Open the calendar and select ``target`` and ``slot``.

        Returns the calendar screen read before the slot was tapped, which also
        holds the continue button unless it stayed disabled. Until ``open_retry_seconds``
        have passed, a notice in place of the calendar, such as the closed-hours notice,
        is closed with Back and the utility tapped again; and
        a date or slot the server does not list yet, right at the opening time, reloads
        the calendar by leaving and entering it again. A fully booked slot and the quota
        notice fail at once.
        """
        deadline = time.monotonic() + self.config.open_retry_seconds
        attempt = 1
        notices = 0
        screen = self._entry
        self._entry = None
        while True:
            screen = self.return_to_utilities(screen)
            # A tap after a notice logs at debug: before the opening one goes every 0.2 s.
            _, screen = self.tap_and_advance(
                screen,
                self.utility,
                self.labels.utility,
                self._calendar_or_notice,
                quiet=notices > 0,
            )
            message = self.notice_text(screen)
            if message is not None:
                refusal = self._refusal(message)
                if isinstance(refusal, QuotaFullError):  # never seen here; a new tap won't help
                    raise refusal
                message = message or "a notice without a message"
                if time.monotonic() >= deadline:
                    raise BookingNotOpenError(
                        f"{target.isoformat()} {slot} not open after {attempt} attempt(s): "
                        f"{message}"
                    )
                notices += 1
                # 0.2 s a try: on 2026-10-19 the list showed 0.1 s after Back.
                log = logger.info if notices == 1 else logger.debug
                log("Not open yet: %s; closing the notice and tapping again", message)
                screen = self.go_back(screen, self._finder(self.utility))
                attempt += 1
                continue
            if notices:
                logger.info("Calendar opened after %d attempt(s)", attempt)
            self.report(EventKind.CALENDAR_OPENED, attempt=attempt)
            try:
                self.select_date(screen, target)
                return self.select_slot(slot)
            except ElementNotFoundError as exc:
                if time.monotonic() >= deadline:
                    raise BookingNotOpenError(
                        f"{target.isoformat()} {slot} not open after {attempt} attempt(s): {exc}"
                    ) from exc
                logger.info("Not open yet (%s); reloading the calendar", exc)
            screen = None
            attempt += 1

    def select_court(self, screen: Screen) -> Screen:
        """Tap the court on the court list ``screen`` and return the booking details page.

        The list moves up 232 px when the service info above it has loaded, and a read
        cannot tell that it is about to (field notes), so a tap placed from the read before
        can land two courts lower: the app opens that court if it is free (S9 booked instead
        of S6 on 2026-10-13 and 17) and does nothing if it is full. The details page names
        the court it opened; another court is left with Back, and the court is tapped again
        where the list shows it then, as it is when the list moved under a tap that opened
        nothing. A tap the app swallowed is tapped again, and the details page is awaited up
        to ``timeout``, as in :meth:`tap_and_advance`.
        """
        name = self.config.court
        node = screen.find(self.court)
        if node is None:
            raise ElementNotFoundError(f"Button not found: {name!r}")
        deadline = time.monotonic() + self.config.timeout
        wrong = 0
        attempt = 1
        while True:
            if node is not None:
                self.tap(node)
            found = self.wait_for(self._court_tapped(node), _retap_wait(deadline))
            if found is None:
                node = self.last_screen.find(self.court)
                attempt += 1
                logger.debug("Next screen missing after %r (attempt %d)", name, attempt)
            elif found[1].find(self.continue_button) is None:
                logger.warning("%r moved on the court list under the tap; tapping it again", name)
                node = found[0]
            elif found[1].find(self.opened_court) is not None:
                logger.info("Tapped %r", name)
                return found[1]
            else:
                wrong += 1
                logger.warning("The app opened another court than %r; going back to the list", name)
                screen = self.go_back(found[1], self._finder(self.court))
                back = self.wait_for(self._finder(self.court), _NEXT_SCREEN_TIMEOUT, screen)
                if back is None:
                    raise NavigationError(f"Could not return to the court list for {name!r}")
                if wrong >= _COURT_ATTEMPTS:
                    break
                node = back[0]
            if time.monotonic() >= deadline:
                break
        if wrong:
            raise NavigationError(f"The app opened another court than {name!r} {wrong} time(s)")
        raise NavigationError(f"Tapped {name!r} but the next screen did not appear")

    def check_single_court(self, screen: Screen) -> Screen:
        """Return the booking details page ``screen`` shows in place of the court list.

        A court list with a single court, such as table tennis's, passes on to that court's
        details page by itself, often before a read shows the list (field notes, "Other
        sports"). The page is awaited until its "Tiếp tục" is enabled, as after a court tap,
        and must name the configured court.
        """
        name = self.config.court
        found = self.wait_for(self._details_page, self.config.timeout, screen)
        if found is None:
            raise ElementNotFoundError(f"{self.labels.continue_!r} stayed disabled")
        screen = found[1]
        if screen.find(self.opened_court) is None:
            raise ElementNotFoundError(f"The app opened its only court, which is not {name!r}")
        logger.info("The app opened its only court, %r", name)
        return screen

    def return_to_utilities(self, screen: Screen | None = None) -> Screen:
        """Navigate to the utilities list from the home, ticket or any inner screen."""
        if screen is None:
            screen = self.snapshot()
        arrived = self._either(self.utility, self.home)
        for _ in range(_BACK_PRESSES):
            if screen.find(self.utility):
                return screen
            if screen.find(self.home):
                _, screen = self.tap_and_advance(
                    screen, self.home, self.labels.home, self._finder(self.utility)
                )
                return screen
            self._warn_about_notice(screen)
            screen = self.go_back(screen, arrived)
        raise NavigationError("Could not return to the utilities list")

    def return_to_home(self, screen: Screen | None = None) -> Screen:
        """Press Back until the home screen shows; Back is never pressed on it (that exits)."""
        if screen is None:
            screen = self.snapshot()
        for _ in range(_BACK_PRESSES):
            if screen.find(self.home):
                return screen
            self._warn_about_notice(screen)
            screen = self.go_back(screen, self._finder(self.home))
        raise NavigationError("Could not return to the home screen")

    # Navigation -------------------------------------------------------------

    def tap_and_advance(
        self,
        screen: Screen,
        target: Match,
        name: str,
        find_next: Finder[T],
        *,
        quiet: bool = False,
    ) -> tuple[T, Screen]:
        """Tap ``target`` on ``screen`` and return what ``find_next`` finds on the next one.

        The next screen is awaited up to ``timeout``, and acted on as soon as a read shows
        it. A tap swallowed by a lagging app is repeated every :data:`_RETAP_AFTER` while
        ``target`` is still shown, never while the app loads the next screen. ``quiet``
        logs the tap at debug level, for a tap repeated many times.
        """
        node = screen.find(target)
        if node is None:
            raise ElementNotFoundError(f"Button not found: {name!r}")
        deadline = time.monotonic() + self.config.timeout
        attempt = 1
        while True:
            if node is not None:
                self.tap(node)
            found = self.wait_for(find_next, _retap_wait(deadline))
            if found is not None:
                (logger.debug if quiet else logger.info)("Tapped %r", name)
                return found
            if time.monotonic() >= deadline:
                raise NavigationError(f"Tapped {name!r} but the next screen did not appear")
            node = self.last_screen.find(target)
            attempt += 1
            logger.debug("Next screen missing after %r (attempt %d)", name, attempt)

    def go_back(self, screen: Screen, arrived: Finder[Node]) -> Screen:
        """Press Back on ``screen`` and return the next screen as soon as it shows.

        That is the first read that shows ``arrived``, or controls of its own while a
        control of ``screen`` is gone. Each screen shows 0.13-0.24 s after Back
        (2026-10-15); waiting for the destination alone cost 2 s per screen on the way.
        Controls are compared, not labels: the status bar's labels change on their own, and
        a screen that only gains controls, such as a ticket still loading, is the same
        screen, where a second Back would go one screen too far. The frame read while a
        screen is built has no controls and is read again. If nothing changed in 2 s, as
        after a Back the app missed, the last read is returned and Back is pressed again.
        """
        before = _controls(screen)

        def next_screen(shown: Screen) -> bool | None:
            controls = _controls(shown)
            if arrived(shown) is not None or (controls and not before <= controls):
                return True
            return None

        self.press_back()
        found = self.wait_for(next_screen, _NEXT_SCREEN_TIMEOUT)
        return found[1] if found is not None else self.last_screen

    def wait_for(
        self, find: Finder[T], timeout: float, screen: Screen | None = None
    ) -> tuple[T, Screen] | None:
        """Read the screen until ``find`` returns a value; ``None`` after ``timeout``.

        ``screen``, if given, is checked first without reading the device again.
        """
        deadline = time.monotonic() + timeout
        while True:
            if screen is None:
                screen = self.snapshot()
            found = find(screen)
            if found is not None:
                return found, screen
            if time.monotonic() >= deadline:
                return None
            time.sleep(_POLL_INTERVAL)
            screen = None

    # Calendar screen --------------------------------------------------------

    def select_date(self, screen: Screen, target: date) -> None:
        """Tap ``target`` in the calendar shown on ``screen``, switching month if needed."""
        match = Match(pattern=self.language.day_pattern(target))
        target_month = month_index(target.year, target.month)
        current: Screen | None = screen
        for attempt in range(5):
            wait = _FIRST_DATE_WAIT if attempt == 0 else _NEXT_DATE_WAIT
            if attempt == 0 and self._month_shown(screen) not in (None, target_month):
                wait = 0  # a month shows only its own days: switch at once
            found = self.wait_for(self._finder(match), wait, current)
            if found is not None:
                self.tap(found[0])
                logger.info("Selected date %s", target.isoformat())
                self.report(EventKind.DATE_SELECTED, date=target.isoformat())
                return
            first_day = self.last_screen.find(self.any_day)
            logger.debug(
                "Date %s not shown; first day listed: %r",
                target.isoformat(),
                first_day.desc if first_day else None,
            )
            shown = self._month_shown(self.last_screen)
            forward = attempt % 2 == 0 if shown is None else shown < target_month
            self._switch_month(self.last_screen, forward)
            current = None
        raise ElementNotFoundError(f"Date {target.isoformat()} is not bookable")

    def select_slot(self, slot: str) -> Screen:
        """Tap ``slot`` once the list shows it, scrolling only while it is hidden.

        The slot is tapped once "Tiếp tục" shows enabled too, or after the list was read
        again for :data:`_CONTINUE_WAIT` with it disabled. Returns the screen read before
        the tap.
        """
        match = Match(prefix=slot)
        button = self.labels.continue_
        deadline = time.monotonic() + self.config.timeout
        swipes = 0
        screen: Screen | None = None
        disabled_since: float | None = None
        while True:
            remaining = max(0.0, deadline - time.monotonic())
            found = self.wait_for(self._finder(self.any_slot), remaining, screen)
            if found is None:
                break
            screen = found[1]
            node = screen.find(match)
            if node is None:
                down = True
            else:
                if self.labels.fully_booked in node.desc:
                    raise SlotUnavailableError(f"Slot {slot} is fully booked")
                position = self._visibility(screen, node)
                if position == "visible":
                    now = time.monotonic()
                    if screen.find(self.continue_button) is None:
                        if disabled_since is None:
                            disabled_since = now
                            logger.debug("%r disabled; reading the slot list again", button)
                        if now - disabled_since < _CONTINUE_WAIT:
                            time.sleep(_POLL_INTERVAL)
                            screen = None
                            continue
                        logger.warning(
                            "%r still disabled after %.0f s; tapping the slot anyway",
                            button,
                            _CONTINUE_WAIT,
                        )
                    elif disabled_since is not None:
                        logger.info("%r enabled after %.2f s", button, now - disabled_since)
                    self.tap(node)
                    time.sleep(_SLOT_SETTLE)
                    logger.info("Selected slot %s (%d swipe(s))", slot, swipes)
                    self.report(EventKind.SLOT_SELECTED, slot=slot, swipes=swipes)
                    return screen
                down = position == "below"
            if swipes >= self.config.max_swipes or time.monotonic() >= deadline:
                break
            self._scroll(screen, down)
            swipes += 1
            screen = self._settled_screen()
        raise ElementNotFoundError(f"Slot {slot} not found after {swipes} swipe(s)")

    # Confirmation screen ----------------------------------------------------

    def locate_checkbox(self, screen: Screen) -> tuple[int, int] | None:
        """Return the tap point of the consent checkbox, or ``None`` if not rendered.

        The checkbox has no label; it is the small node beside its caption,
        preferring clickable and smaller nodes. Nodes that are not level with the
        caption are never returned.
        """
        caption = screen.find(self.agree)
        if caption is None:
            return None
        width, _ = screen.size
        candidates = [
            node for node in screen.nodes if is_checkbox_beside(node.box, caption.box, width)
        ]
        if not candidates:
            return None
        node = min(candidates, key=lambda n: (not n.clickable, _area(n)))
        logger.debug("Checkbox found beside caption at %s", node.box)
        return node.center

    def read_confirmation(self, screen: Screen, slot: str, target: date) -> Booked:
        """Read the date, slot and court that the confirmation page on ``screen`` books.

        The court is checked on the booking details page already (:meth:`select_court`),
        so a difference here is only logged as a warning and the round still confirms.
        """
        labels = self.labels
        booked = Booked(shown_court=screen.line_after(labels.booked_place))
        time_text = screen.line_after(labels.booked_time)
        parsed = None if time_text is None else parse_booked_time(time_text)
        if parsed is not None:
            booked.shown_date, booked.shown_slot = parsed[0].isoformat(), parsed[1]
        shown = (booked.shown_date, booked.shown_slot, booked.shown_court)
        wanted = (target.isoformat(), slot, self.config.court)
        if None in shown:
            logger.warning("Could not read the date, slot and court on the confirmation page")
        elif shown != wanted:
            logger.warning(
                "The confirmation page books %s %s on %s, not %s %s on %s; confirming anyway",
                *shown,
                *wanted,
            )
        else:
            logger.info("Confirmation page: %s %s on %s", *shown)
        return booked

    def read_ticket(self, screen: Screen, booked: Booked) -> None:
        """Note the ticket's status on ``screen``, the first read that showed the ticket.

        The ticket loads in steps: its title first, then the status (seen "Đang xử lý" at
        06:00), the time and the court. Waiting for the rest would delay the next round, so
        only this read counts.
        """
        status = screen.find(self.processing) or screen.find(self.registered)
        booked.ticket_status = None if status is None else status.desc
        logger.debug("Ticket shown, status %r", booked.ticket_status)

    def accept_and_confirm(self, point: tuple[int, int], dry_run: bool) -> Screen | None:
        """Tick the consent checkbox at ``point`` and submit the booking.

        The confirm button only becomes clickable once the box is ticked, which
        verifies the tick. The round is booked only once the ticket shows; a notice
        dialog, such as a slot taken a moment earlier by someone else, fails it, and so
        does neither in ``timeout``: better a booking reported missing than a missing one
        reported booked. "Xác nhận" is tapped again every :data:`_CONFIRM_RETAP_AFTER`
        while the page still shows it enabled, never while the next screen is built. A
        notice after such a tap may answer the second tap of a booking the first one made,
        so it leaves the outcome unknown. Returns the screen that showed the ticket, or
        ``None`` in a dry run.
        """
        deadline = time.monotonic() + self.config.timeout
        while True:
            ticked = time.monotonic()
            self.tap_point(*point)
            found = self.wait_for(self._finder(self.confirm_button), _CHECKBOX_TIMEOUT)
            if found is not None:
                break
            if time.monotonic() >= deadline:
                raise NavigationError("Checkbox tapped but the confirm button stayed disabled")
            point = self.locate_checkbox(self.last_screen) or point
        logger.info("Accepted terms")
        self.report(EventKind.TERMS_ACCEPTED)

        if dry_run:
            logger.info("Dry run: skipping final confirmation")
            return None
        time.sleep(max(0.0, ticked + _TERMS_SETTLE - time.monotonic()))
        button: Node | None = found[0]
        name = found[0].desc
        deadline = time.monotonic() + self.config.timeout
        taps = 0
        tapped = 0.0
        while True:
            if button is not None:
                if taps:
                    logger.info(
                        "%r tapped again %.1f s after the last tap with the page unchanged "
                        "(attempt %d)",
                        name,
                        time.monotonic() - tapped,
                        taps + 1,
                    )
                tapped = time.monotonic()
                self.tap(button)
                taps += 1
            outcome = self.wait_for(
                self._after_confirm, _retap_wait(deadline, _CONFIRM_RETAP_AFTER)
            )
            if outcome is not None:
                break
            if time.monotonic() >= deadline:
                raise BookingUnconfirmedError(
                    "Outcome unknown: neither the ticket nor a notice showed "
                    f"{self.config.timeout:.0f} s after confirming (taps on {name!r}: {taps}); "
                    "check the app"
                )
            button = self.last_screen.find(self.confirm_button)
        message = self.notice_text(outcome[1])
        if message is not None and taps > 1:
            raise BookingUnconfirmedError(
                f"Outcome unknown: a notice after {taps} taps on {name!r}: "
                f"{message or 'no message'}; an earlier tap may have booked, check the app"
            )
        if message is not None:
            raise self._refusal(message)
        logger.info("Booking confirmed")
        return outcome[1]

    # Dialogs ----------------------------------------------------------------

    def notice_text(self, screen: Screen) -> str | None:
        """Return the message of the app's notice dialog on ``screen``, or ``None``.

        The dialog's title node spans the whole dialog and holds its buttons; a node
        with the same label but no button inside, such as a tab, is not a dialog. The
        message is every other label inside the title that is not a button.
        """
        for title in screen.find_all(self.notice):
            inner = [node for node in screen.nodes if is_inside(node.box, title.box)]
            if not any(node.clickable and node is not title for node in inner):
                continue
            return " ".join(
                node.desc
                for node in inner
                if node.desc and not node.clickable and node.desc != title.desc
            )
        return None

    def _warn_about_notice(self, screen: Screen) -> None:
        """Log a notice about to be closed with Back; it may belong to the round before."""
        message = self.notice_text(screen)
        if message is not None:
            logger.warning("Closing a notice of the app: %s", message or "no message")

    # Device commands --------------------------------------------------------

    def snapshot(self) -> Screen:
        """Read every element of the current screen with one command.

        A screen that differs from the previous read is logged, so the debug log shows
        every screen a run went through, also the ones a failure or a popup left behind.
        """
        self.commands += 1
        screen = Screen.parse(self.device.dump_hierarchy(compressed=False))
        if screen.nodes != self.last_screen.nodes:
            log_screen(screen, "Screen")
        self.last_screen = screen
        return screen

    def tap(self, node: Node) -> None:
        self.tap_point(*node.center, label=node.desc)

    def tap_point(self, x: float, y: float, label: str = "") -> None:
        """Tap ``(x, y)``; ``label`` names the element tapped.

        The driver clicks the element with that label where it is now, which may be away
        from ``(x, y)`` if the screen moved since it was read; uiautomator2 taps the point.
        """
        self.commands += 1
        logger.debug("Tap %s(%d, %d)", f"{label!r} at " if label else "", x, y)
        self.device.click(x, y, label=label)

    def press_back(self) -> None:
        self.commands += 1
        logger.debug("Press Back")
        self.device.press("back")

    # Helpers ----------------------------------------------------------------

    def _finder(self, match: Match) -> Finder[Node]:
        return lambda screen: screen.find(match)

    def _either(self, first: Match, second: Match) -> Finder[Node]:
        return lambda screen: screen.find(first) or screen.find(second)

    def _find_language(self, screen: Screen) -> AppLanguage | None:
        """Return the language whose home or utility button ``screen`` shows.

        Their labels differ in each language (field notes), so no screen shows two.
        """
        for language in self.languages:
            labels = language.labels
            for label in (labels.home, labels.utility):
                if label and screen.find(Match(desc=label, clickable=True)) is not None:
                    return language
        return None

    def _after_confirm(self, screen: Screen) -> bool | None:
        """Return ``True`` once the ticket's title or a notice shows.

        The confirmation page stays about 1 s while the server answers, then a frame with
        no labels shows while the next screen is built, before the ticket and before a
        notice alike (2026-10-15), so the page going away does not tell the outcome.
        """
        if screen.find(self.ticket) is not None or self.notice_text(screen) is not None:
            return True
        return None

    def _find_calendar(self, screen: Screen) -> Node | None:
        return (
            screen.find(self.any_day)
            or screen.find(self.prev_month)
            or screen.find(self.next_month)
        )

    def _calendar_or_notice(self, screen: Screen) -> bool | None:
        """Return ``True`` once the calendar or a notice shows, such as the closed-hours one.

        The notice showed 0.05 s after a tap on the utility before 06:00 (2026-10-19), in
        place of the calendar; waiting for the calendar alone then cost the round 10 s.
        """
        if self._find_calendar(screen) is not None or self.notice_text(screen) is not None:
            return True
        return None

    def _court_tapped(self, tapped: Node | None) -> Finder[Node]:
        """Find the details page's continue button, or the court moved on a list left as is.

        The details page is known by its residents caption, which can show before the
        continue button is enabled, so both are awaited. A list still shown
        :data:`_MOVED_COURT_WAIT` after the tap, with the court somewhere else than
        ``tapped``, ignored the tap; the court is returned where it shows now.
        """
        since = time.monotonic()

        def find(screen: Screen) -> Node | None:
            button = self._details_page(screen)
            if button is not None:
                return button
            court = screen.find(self.court)
            if (
                court is not None
                and tapped is not None
                and court.box != tapped.box
                and time.monotonic() - since >= _MOVED_COURT_WAIT
            ):
                return court
            return None

        return find

    def _courts_or_details(self, screen: Screen) -> Node | None:
        """Return the court list's heading, or the booking details page's caption."""
        return screen.find(self.court_list) or screen.find(self.residents)

    def _court_or_details(self, screen: Screen) -> Node | None:
        """Return the court on the list, or the caption of the details page it passed on to."""
        return screen.find(self.any_court) or screen.find(self.residents)

    def _details_page(self, screen: Screen) -> Node | None:
        """Return the booking details page's continue button once it is enabled."""
        button = screen.find(self.continue_button)
        if button is not None and screen.find(self.residents) is not None:
            return button
        return None

    def _after_calendar(self, screen: Screen) -> Node | None:
        """Return what shows after the calendar's "Tiếp tục", once it shows.

        That is the court list's heading, the venue to tap, the booking details page's
        caption or a notice's title. A utility with a single court shows its details page in
        place of the court list. The quota notice shows in place of the next screen (field
        notes, "Dialogs"); waiting for the courts alone cost the round ``timeout``.
        """
        found = (
            screen.find(self.court_list) or self._venue_entry(screen) or screen.find(self.residents)
        )
        if found is None and self.notice_text(screen) is not None:
            return screen.find(self.notice)
        return found

    def _refusal(self, message: str) -> BookingRejectedError:
        """Return the error for the app's notice ``message`` in place of the next screen."""
        quota = self.labels.quota_full
        if quota and quota in message:
            return QuotaFullError(f"Booking quota used up: {message}")
        return BookingRejectedError(f"The app refused the booking: {message or 'no message'}")

    def _venue_entry(self, screen: Screen) -> Node | None:
        """Return the venue to tap below the venues' heading, once it is listed.

        The heading shows a read or more before the venues in some reads (8 of 30 by
        2026-10-23). A single venue is tapped whatever its name; of several, the one that
        names ``venue_keyword``.
        """
        heading = screen.find(self.venue_list)
        if heading is None:
            return None
        venues = [
            node
            for node in screen.nodes
            if node.clickable and node.desc and node.box[1] >= heading.box[3]
        ]
        if len(venues) == 1:
            return venues[0]
        keyword = self.config.venue_keyword
        return next((node for node in venues if keyword and keyword in node.desc), None)

    def _visibility(self, screen: Screen, node: Node) -> str:
        """Return ``visible``, ``below`` or ``above`` relative to the tappable area.

        Dump bounds are clipped to what is shown, so a partly hidden slot is
        shorter than a full one. The sticky bottom button counts as hidden area.
        """
        _, height = screen.size
        button = screen.find(Match(desc=self.labels.continue_))
        bottom_limit = button.box[1] if button is not None else height
        full_height = max(n.height for n in screen.find_all(self.any_slot))
        if node.box[3] <= bottom_limit and node.height >= full_height * _MIN_VISIBLE_RATIO:
            return "visible"
        return "below" if node.center[1] > height / 2 else "above"

    def _scroll(self, screen: Screen, down: bool) -> None:
        width, height = screen.size
        start, end = (0.62, 0.38) if down else (0.38, 0.62)
        self.commands += 1
        logger.debug("Swipe %s", "down the list" if down else "up the list")
        self.device.swipe(width * 0.5, height * start, width * 0.5, height * end, _SWIPE_SECONDS)

    def _settled_screen(self) -> Screen:
        """Read the screen until the slot list stops moving after a swipe."""
        deadline = time.monotonic() + _SETTLE_TIMEOUT
        previous = None
        while True:
            screen = self.snapshot()
            boxes = [node.box for node in screen.find_all(self.any_slot)]
            if boxes == previous or time.monotonic() >= deadline:
                return screen
            previous = boxes
            time.sleep(_POLL_INTERVAL)

    def _month_shown(self, screen: Screen) -> int | None:
        """Return the month index of the first day ``screen`` lists, ``None`` without one."""
        first_day = screen.find(self.any_day)
        return None if first_day is None else self.language.month_index_from_label(first_day.desc)

    def _switch_month(self, screen: Screen, forward: bool) -> None:
        button = screen.find(self.next_month if forward else self.prev_month)
        if button is not None:
            self.tap(button)
        else:
            x_ratio, y_ratio = self.config.next_month_xy if forward else self.config.prev_month_xy
            width, height = screen.size
            self.tap_point(width * x_ratio, height * y_ratio)
        logger.debug("Switched to %s month", "next" if forward else "previous")


def log_screen(screen: Screen, title: str) -> None:
    """Log every labelled or clickable element of ``screen`` under ``title`` (debug).

    One record per screen, so the history writes one row for it instead of one per element.
    """
    lines = screen.describe()
    logger.debug("%s (%d elements):%s", title, len(lines), "".join(f"\n  {x}" for x in lines))


def _retap_wait(deadline: float, after: float = _RETAP_AFTER) -> float:
    """Return how long to wait for the next screen before a tap may be repeated."""
    return min(after, max(0.0, deadline - time.monotonic()))


def _controls(screen: Screen) -> set[Node]:
    """Return the clickable elements of ``screen``, except one that covers all of it.

    The frame read while a screen is built has none: its only clickable element spans the
    whole screen (2026-10-15).
    """
    whole = (0, 0, *screen.size)
    return {node for node in screen.nodes if node.clickable and node.box != whole}


def _area(node: Node) -> int:
    left, top, right, bottom = node.box
    return (right - left) * (bottom - top)
